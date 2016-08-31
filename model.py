import datetime
import random

from google.appengine.api import memcache
from google.appengine.ext import db


def from_milliseconds(millis):
    return datetime.datetime.utcfromtimestamp(millis / 1000)


def to_milliseconds(date_time):
    delta = date_time - from_milliseconds(0)
    return int(round(delta.total_seconds() * 1000))


class GlobalPreferences(db.Expando):

    # github integration preference
    __INTEGRATE_WITH_GITHUB__ = 'integrate_with_github'

    """
    Global preferences that can control the behavior of the crash reporter.
    """
    property_name = db.StringProperty()
    property_value = db.StringProperty()

    @classmethod
    def key_name(cls, property_name):
        return cls.kind() + '_' + property_name

    @classmethod
    def get_property(cls, property_name, default_value=None):
        key_name = GlobalPreferences.key_name(property_name)
        preference = GlobalPreferences.get_by_key_name(key_names=key_name)
        if preference is None:
            return default_value
        else:
            return preference.property_value

    @classmethod
    def update(cls, property_name, property_value):
        key_name = GlobalPreferences.key_name(property_name)
        preference = GlobalPreferences.get_or_insert(key_name, property_name=property_name)
        preference.property_value = property_value
        # update
        db.put(preference)
        return preference


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
    name = db.StringProperty(required=True)  # key_name and not the sharded key name
    labels = db.StringListProperty(default=[])
    crash = db.TextProperty(required=True)
    fingerprint = db.StringProperty(required=True)
    date_time = db.DateTimeProperty(required=True, auto_now_add=True)
    count = db.IntegerProperty(default=0)
    # state can be one of 'unresolved'|'pending'|'submitted'|'resolved'
    state = db.StringProperty(default='unresolved')
    # github issue
    issue = db.StringProperty(required=False)
    # argv
    argv = db.StringListProperty(default=[])
    # reflects the schema version
    version = db.StringProperty(default='2')

    @classmethod
    def get_count(cls, name):
        cache_key = CrashReport.count_cache_key(name)
        total = memcache.get(cache_key)
        if total is None:
            total = 0
            q = CrashReport.all()
            q.filter('name = ', name)
            for entity in q.run():
                total += entity.count
            memcache.set(cache_key, str(total))
        return int(total)

    @classmethod
    def clear_properties_cache(cls, name):
        keys = list()
        keys.extend(
            CrashReport.recent_crash_property_key(name, key) for key in
            ['date_time', 'state', 'labels', 'issue', 'argv']
        )
        memcache.delete_multi(keys=keys)

    @classmethod
    def _most_recent_property(
            cls, name, property_name, default_value=None, serialize=lambda x: x, deserialize=lambda x: x, ttl=120):

        cache_key = CrashReport.recent_crash_property_key(name, property_name)
        most_recent_value = memcache.get(cache_key)
        if most_recent_value is None:
            most_recent = 0
            most_recent_value = default_value

            q = CrashReport.all()
            q.filter('name = ', name)
            for entity in q.run():
                in_millis = to_milliseconds(entity.date_time)
                if most_recent <= in_millis:
                    most_recent = in_millis
                    most_recent_value = serialize(entity.__getattribute__(property_name))
            memcache.set(cache_key, most_recent_value, ttl)
        to_return = deserialize(most_recent_value)
        return to_return

    @classmethod
    def most_recent_crash(cls, name):
        return CrashReport._most_recent_property(
            name, 'date_time', serialize=lambda x: str(to_milliseconds(x)), deserialize=lambda x: int(x))

    @classmethod
    def most_recent_labels(cls, name):
        return CrashReport._most_recent_property(
            name, 'labels',
            default_value=list(),
            serialize=lambda x: ','.join(x),
            deserialize=lambda x: x.split(','))

    @classmethod
    def most_recent_state(cls, name):
        return CrashReport._most_recent_property(name, 'state', default_value='unresolved')

    @classmethod
    def most_recent_issue(cls, name):
        return CrashReport._most_recent_property(name, 'issue')

    @classmethod
    def most_recent_argv(cls, name):
        return CrashReport._most_recent_property(name, 'argv', default_value=list())

    @classmethod
    def add_or_remove(cls, fingerprint, crash, argv=None, labels=None, is_add=True, delta=1):
        # use an issue if one already exists
        issue = CrashReport.most_recent_issue(CrashReport.key_name(fingerprint))
        key_name = CrashReport.key_name(fingerprint)
        config = ShardedCounterConfig.get_sharded_config(key_name)
        shards = config.shards
        shard_to_use = random.randint(0, shards-1)
        shard_key_name = key_name + '_' + str(shard_to_use)
        if not argv:
            argv = []
        crash_report = CrashReport \
            .get_or_insert(shard_key_name,
                           name=key_name,
                           crash=crash,
                           fingerprint=fingerprint,
                           argv=argv,
                           labels=labels,
                           issue=issue)
        if is_add:
            crash_report.count += delta
            crash_report.put()
            # update caches
            memcache.incr(CrashReport.count_cache_key(key_name), delta, initial_value=0)
        else:
            crash_report.count -= delta
            crash_report.put()
            memcache.decr(CrashReport.count_cache_key(key_name), delta)

        # clear properties cache
        CrashReport.clear_properties_cache(key_name)
        return crash_report

    @classmethod
    def get_crash(cls, fingerprint):
        q = CrashReport.all()
        q.filter('name =', CrashReport.key_name(fingerprint))
        crash_report = q.get()
        if not crash_report:
            return None
        else:
            return crash_report

    @classmethod
    def key_name(cls, name):
        return cls.kind() + '_' + name

    @classmethod
    def count_cache_key(cls, name):
        return 'total_{0}'.format(name)

    @classmethod
    def recent_crash_property_key(cls, name, property_name):
        return 'most_recent_{0}/{1}'.format(name, property_name)

    @classmethod
    def to_json(cls, entity):
        return {
            'key': unicode(entity.key()),
            'crash': entity.crash,
            'argv': CrashReport.most_recent_argv(entity.name),
            'labels': CrashReport.most_recent_labels(entity.name),
            'fingerprint': entity.fingerprint,
            'time': CrashReport.most_recent_crash(entity.name),  # in millis
            'count': CrashReport.get_count(entity.name),
            'state': CrashReport.most_recent_state(entity.name),
            'issue': CrashReport.most_recent_issue(entity.name)
        }


class Link(object):
    """
    Represents a link (essentially contains the url, title and active properties).
    """
    def __init__(self, title, url, active=False):
        self.title = title
        self.url = url
        self.active = active
