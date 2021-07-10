import os
import secrets

import requests
from flask import abort, Flask, jsonify, redirect, render_template, request, session
from PIL import Image

import mosaic_bot.hash
from mosaic_bot import db, image, DATA_PATH
from mosaic_bot.credentials import MOSAIC_CLIENT_ID, MOSAIC_CLIENT_SECRET, OAUTH_REDIRECT_URI, SERVER_SECRET_KEY

JSONIFY_PRETTYPRINT_REGULAR = False
app = Flask('mosaic_server', template_folder = DATA_PATH/'templates')
app.secret_key = SERVER_SECRET_KEY


def check_cookies():
    if request.cookies.get('alpha-tester') != 'yes':
        return redirect('/alpha-tester')


@app.route('/')
def landing():
    if c := check_cookies():
        return c
    return redirect('/gallery')


@app.route('/alpha-tester', methods = ['GET', 'POST'])
def tester():
    if request.method == 'GET':
        return """ <title> access denied </title>
        <p>If you are an alpha tester, you should have received your access code. Please enter your access code to continue </p>
        <form method='post'>
        <label for='access-code'>Code </label> 
        <input id='access-code' name='access-code' type='text'>
        <input type='submit'>
        </form>
        """

    if request.method == 'POST':
        if request.form.get('access-code') == 'your access code':
            return '<script>' \
                   'document.cookie = "alpha-tester=yes; expires=Mon, 1 Nov 2021 12:00:00 UTC; path=/";' \
                   'alert("access granted"); location.href="/";'\
                   '</script>'
            # if you took the trouble of looking at this code to figure out what the access code is
            # then just add the cookie yourself. this is only designed to stop bots and random people online.
        else:
            return 'Nah', 401


def encode(path):
    return image.image_to_data(Image.open(path), True)


@app.route('/gallery')
def gallery():
    if c := check_cookies():
        return c
    return render_template('gallery.jinja2')


@app.route('/upload')
def upload():
    if c := check_cookies():
        return c
    username=session.get('username')
    return render_template('upload.jinja2',username=username)


@app.route('/login')
def login():
    state = secrets.token_urlsafe(32)
    session.clear()
    session['state'] = state
    return redirect(f'https://discord.com/api/oauth2/authorize?response_type=code&client_id={MOSAIC_CLIENT_ID}'
                    f'&scope=identify&state={state}&redirect_uri=http://localhost:5000/api/oauth_callback')


@app.route('/logout')
def logout():
    session.clear()
    return 'You are now logged out'


@app.route('/api/oauth_callback', methods = ['GET'])
def oauth_callback():
    state = request.args.get('state', 'no state')
    code = request.args.get('code')
    try:
        if state != session.pop('state'):
            abort(400, 'Mismatching state. If you have no clue what happened, '
                       'someone probably is doing an MITM attack on you.')
    except KeyError:
        abort(400,'State verification failed. Please enable cookies')
    r=requests.post('https://discord.com/api/v8/oauth2/token', data = {
        'client_id'    : MOSAIC_CLIENT_ID,
        'client_secret': MOSAIC_CLIENT_SECRET,
        'code'         : code,
        'redirect_uri' : OAUTH_REDIRECT_URI,
        'grant_type'   : 'authorization_code',
        'scope'        : 'identify'
    })
    r.raise_for_status()
    oauth_data=r.json()
    token=oauth_data['access_token']
    token_type=oauth_data['token_type']
    r=requests.get('https://discord.com/api/v8/users/@me', headers={
        'Authorization':f'{token_type} {token}'
    })
    r.raise_for_status()
    user_data=r.json()
    uid=user_data['id']
    name=user_data['username']
    tag=user_data['discriminator']
    session['id']=uid
    session['username']=f'{name}#{tag}'
    return redirect('/upload')




@app.route('/api/gallery', methods = ['GET'])
def api_gallery():
    res = []
    for name, h, width, height, time in db.list_images():
        path = 'image/' + mosaic_bot.hash.encode_hash(h) + '.png'
        res.append({
            'name'  : name,
            'path'  : path,
            'time'  : time,
            'width' : width,
            'height': height,
            'id'    : str(h)  # js number precision is...problematic for 144 bit integers
        })
    return jsonify(res)


if __name__ == '__main__':
    app.run(debug = False)
