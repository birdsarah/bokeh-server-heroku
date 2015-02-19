# To setup locally

$ conda install --file conda-requirements.txt
$ foreman start

Edit config.py as appropriate


# To setup on heroku

$ heroku config:set BUILDPACK_URL=https://github.com/thenovices/heroku-buildpack-scipy
$ heroku config:set FLASK_SECRET_KEY='an actually secret key'
$ heroku config:set BOKEH_SECRET_KEY='another secret key'

