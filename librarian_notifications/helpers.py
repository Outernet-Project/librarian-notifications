from bottle import request

from librarian_core.contrib.templates.decorators import template_helper

from .notifications import to_dict, Notification, NOTIFICATION_COLS


FIXED_COLS = ['n.' + c for c in NOTIFICATION_COLS]


def get_user_groups(user):
    if user:
        groups = tuple(g.name for g in request.user.groups)
    else:
        user = None
        groups = ('guest',)
    return user, groups


def get_notifications(db=None):
    db = db or request.db.notifications
    user = request.user.username if request.user.is_authenticated else None
    user, groups = get_user_groups(user)
    where_cond = ('((t.target_type = \'group\' AND t.target IN %s) OR '
                  '(t.target_type = \'user\' AND t.target = %s) OR '
                  '(t.target_type = \'group\' AND t.target = \'all\')) AND'
                  '(t.notification_id = n.notification_id) AND'
                  '(n.dismissable = false OR n.read_at IS NULL)')
    target_query = db.Select(sets='notification_targets t, notifications n',
                             what=FIXED_COLS,
                             where=where_cond)
    for row in db.fetchiter(target_query, (groups, user)):
        notification = Notification(**to_dict(row))
        if not notification.is_read:
            yield notification


def _get_notification_count(db):
    db = db or request.db.notifications
    user = request.user.username if request.user.is_authenticated else None
    user, groups = get_user_groups(user)
    where_cond = ('((t.target_type = \'group\' AND t.target IN %s) OR'
                  '(t.target_type = \'user\' AND t.target = %s) OR '
                  '(t.target_type = \'group\' AND t.target = \'all\')) AND'
                  '(t.notification_id = n.notification_id) AND'
                  '(n.dismissable = false OR n.read_at IS NULL)')
    count_query = db.Select('COUNT(*) as count',
                            sets='notification_targets t, notifications n',
                            where=where_cond)
    unread_count = db.fetchone(count_query, (groups, user))['count']
    unread_count -= len(request.user.options.get('notifications', {}))
    return unread_count


@template_helper
def get_notification_count(db=None):
    key = 'notification_count_{0}'.format(request.session.id)
    count = request.app.supervisor.exts(onfail=None).cache.get(key)
    if count:
        return count

    count = _get_notification_count(db)
    request.app.supervisor.exts.cache.set(key, count)
    return count
