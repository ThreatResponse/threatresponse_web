# python-threatresponse_webapp



Note this app now requires Redis on localhost running.
`redis-server`

To start this project:

SASS based on this tutorial https://adambard.com/blog/fresh-flask-setup/

```
pip install -r requirements.txt
sudo gem install sass
sudo npm install -g bower coffee-script
```

```
bower init
bower install -S jquery

```

```
#run celery from a seperate console also inside your virtualenv
celery -A threatresponse.tasks worker
```


## Todo

Automate spin up of timesketch via docker-compose
Import timeline from acquisition using tsctl... ( currently only appears to work as csv )
Import each plaso snapshot using called via a docker exec
psort.py -o timesketch snap-28e69677.plaso --name my_timeline
