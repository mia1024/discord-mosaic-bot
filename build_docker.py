import subprocess, os, sys, datetime, shutil, pathlib

in_docker = 'docker' in open('/proc/1/cgroup').read()

os.chdir(os.path.dirname(__file__))
if not in_docker:
    dirty = subprocess.run('git diff HEAD', stdout = subprocess.PIPE, shell = True).stdout
    if dirty:
        if len(sys.argv) > 1 and sys.argv[1] == 'dev':
            from mosaic_bot.__build__ import build_hash as hash

            sys.argv.pop(1)
        else:
            print('ERROR: working tree dirty. Please commit all changes first', file = sys.stderr)
            exit(1)
    else:
        hash = subprocess.run('git rev-parse HEAD', stdout = subprocess.PIPE, shell = True).stdout.decode()

    root = pathlib.Path(__file__).resolve().parent
    # shutil.rmtree(root / 'data' / 'static',ignore_errors = True)
    # shutil.copytree(root / 'mosaic_bot/server/static', root / 'data/static')
    args = f'docker build -f Dockerfile -t mia1024/discord-mosaic-bot:latest -t mia1024/discord-mosaic-bot:{hash[:6]} --build-arg MOSAIC_BUILD_HASH={hash} .'.split()
    args.extend(sys.argv[1:])

    os.environ['DOCKER_BUILDKIT'] = '1'
    os.execvp('docker', args)
else:
    hash = os.environ.get('MOSAIC_BUILD_HASH')
    if not hash:
        print("ERROR: build arg MOSAIC_BUILD_HASH is not supplied", file = sys.stderr)
        exit(1)
    f = open('mosaic_bot/__build__.py', 'w')
    f.write(f'build_time="{datetime.datetime.utcnow().isoformat()}";')
    f.write(f'build_hash="{hash}";')
    f.write(f'build_type="release"\n')
    f.close()
