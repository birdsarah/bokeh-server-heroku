### To setup locally

    $ conda install --file conda-requirements.txt
    $ foreman start

Edit `config.py` as appropriate


### To setup on heroku

Configure heroku to use the conda buildpack and add your secret keys:

    $ heroku config:set BUILDPACK_URL=https://github.com/thenovices/heroku-buildpack-scipy
    $ heroku config:set FLASK_SECRET_KEY='an actually secret key'
    $ heroku config:set BOKEH_SECRET_KEY='another secret key'

To run with redis, add the heroku add on rediscloud (the 25 level is free):

    $ heroku addons:add rediscloud:25 

Then, as normal, push to heroku to deploy
