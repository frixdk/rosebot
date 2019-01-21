# rosebot
```
$ virtualenv -p python3 roseenv
$ source roseenv/bin/activate
$ pip3 install -r requirements/base.txt
$ python manage.py migrate
$ python manage.py testmsg
```

# How to update on server
```
$ git fetch origin
$ git reset --hard origin/master
$ systemctl restart emperor.uwsgi.service
If changes to requirements dont forget to pip install in the virtual env
```
