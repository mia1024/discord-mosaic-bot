import subprocess,os,sys,datetime
from mosaic_bot import __version__
in_docker = 'docker' in open('/proc/1/cgroup').read()

os.chdir(os.path.dirname(__file__))
if not in_docker:
    dirty=subprocess.run('git diff HEAD',stdout = subprocess.PIPE,shell=True).stdout
    if dirty:
        print('ERROR: working tree dirty. Please commit all changes first',file = sys.stderr)
        exit(1)
    hash=subprocess.run('git rev-parse HEAD',stdout = subprocess.PIPE,shell=True).stdout.decode()
    args=f'docker build -t jeriewang/mosaic-bot:latest -t jeriewang/mosaic-bot:{hash[:6]} --build-arg MOSAIC_BUILD_HASH={hash} .'.split()
    args.extend(sys.argv[1:])
    os.execvp('docker',args)
else:
    hash=os.environ.get('MOSAIC_BUILD_HASH')
    if not hash:
        print("ERROR: build arg MOSAIC_BUILD_HASH is not supplied",file=sys.stderr)
        exit(1)
    f=open('mosaic_bot/__build__.py','w')
    f.write(f'build_time="{datetime.datetime.utcnow().isoformat()}";')
    f.write(f'build_hash="{hash}";')
    f.write(f'build_type="release"\n')
    f.close()