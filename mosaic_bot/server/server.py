from flask import Flask,request,redirect,render_template
from mosaic_bot import db, IMAGE_DIR, image
from PIL import Image
from functools import lru_cache
import os

app=Flask('mosaic_server',template_folder = os.path.abspath(os.path.dirname(__file__))+'/templates')

def check_cookies():
    if request.cookies.get('alpha-tester')!='yes':
        return redirect('/alpha-tester')

@app.route('/')
def landing():
    return 'Page under construction. Please come back later. Perhaps check <a href="/gallery">gallery</a>?'

@app.route('/alpha-tester',methods=['GET','POST'])
def tester():
    if request.method=='GET':
        return """ <title> access denied </title>
        <p>If you are an alpha tester, you should have received your access code. Please enter your access code to continue </p>
        <form method='post'>
        <label for='access-code'>Code </label> 
        <input id='access-code' name='access-code' type='text'>
        <input type='submit'>
        </form>
        """

    if request.method=='POST':
        if request.form.get('access-code')=='your access code':
            return 'Access granted <script>document.cookie = "alpha-tester=yes; expires=Thu, 1 Apr 2021 12:00:00 UTC; path=/";</script>'
        else:
            return 'Nah', 401

def encode(path):
    return image.image_to_data(Image.open(path),True)

@app.route('/gallery')
@lru_cache() # for development only. actual server will use reverse proxy cache
def gallery():
    check_cookies()
    return render_template('gallery.jinja2',images=db.list_images(),encode=encode)

if __name__=='__main__':
    app.run(debug = True)