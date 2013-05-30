import random
import datetime
from google.appengine.api import memcache
from google.appengine.ext import db


class ShardedCounterConfig(db.Expando):
    """
    Represents the sharded counter config, that helps us figure out how many shards to use for a sharded counter
    __key__ == name property in ShardedCounter
    """
    name = db.StringProperty(required=True)
    shards = db.IntegerProperty(default=1)

    @classmethod
    def cache_key(cls, name):
        return 'shard_config_' + name

    @classmethod
    def get_sharded_config(cls, name):
        cache_key = ShardedCounterConfig.cache_key(name)
        config = memcache.get(cache_key)
        if not config:
            ''' Try fetching from datastore '''
            config = ShardedCounterConfig.get_or_insert(name, name=name, shards=20)
            memcache.set(cache_key, config, time=86400)
        return config


class CrashReport(db.Expando):
    """
    Represents an Crash Report item
    """
    name = db.StringProperty(required=True)
    item_id = db.StringProperty(required=True)
    time = db.DateTimeProperty(required=True, default=datetime.datetime.utcnow())
    count = db.IntegerProperty(default=0)

    @classmethod
    def get_count(cls, key_name):
        total = memcache.get(key_name)
        if total is None:
            total = 0
            q = CrashReport.all()
            q.filter('name = ', key_name)
            for counter in q.run():
                total += counter.count
            memcache.set(key_name, str(total))
        ''' total can be a string (when cached) '''
        return int(total)

    @classmethod
    def add_or_remove(cls, item_id, is_add=True, delta=1):
        key_name = CrashReport.key_name(item_id)
        config = ShardedCounterConfig.get_sharded_config(key_name)
        shards = config.shards
        shard_to_use = random.randint(0, shards-1)
        shard_key_name = key_name + '_' + str(shard_to_use)
        counter = CrashReport.get_or_insert(shard_key_name, name=key_name, item_id=item_id)
        if is_add:
            counter.count += delta
            counter.put()
            memcache.incr(key_name, delta)
        else:
            counter.count -= delta
            counter.put()
            memcache.decr(key_name, delta)

    @classmethod
    def key_name(cls, name):
        return cls.kind() + '_' + name

    @classmethod
    def to_json(cls, entity):
        return {
            'item_id': entity.item_id,
            'time': int(round(entity.time * 1000)), # in millis
            'count': cls.get_count(cls.key_name(entity.item_id))
        }


class Link(object):
    '''
    Represents a link (essentially contains the url, title and active properties).
    '''
    def __init__(self, title, url, active=False):
        self.title = title
        self.url = url
        self.active = active
