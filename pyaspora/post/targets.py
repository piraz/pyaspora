from pyaspora.contact.views import json_contact
from pyaspora.roster.views import json_group


class Target:
    @classmethod
    def _user_bothway_contacts(cls, user, parent=None):
        return cls._contacts_intersect_interested(
            user,
            user.contact.friends(),
            parent
        )

    @classmethod
    def _user_bothway_contacts_for_post(cls, user, post):
        return cls._post_intersect_contacts(
            post,
            cls._user_bothway_contacts(user)
        )

    @classmethod
    def _post_intersect_contacts(cls, post, contacts):
        parent_shared_with = set(s.contact_id for s in post.shares)
        return [c for c in contacts if c.id in parent_shared_with]

    @classmethod
    def _contacts_intersect_interested(cls, user, contacts, parent=None):
        return [
            c for c in contacts
            if cls._contact_wants_to_hear_from_user(user.contact, c, parent)
        ]

    @classmethod
    def _make_self_share(cls, post, on_wall=False):
        post.share_with([post.author], show_on_wall=on_wall)

    @classmethod
    def _contact_wants_to_hear_from_user(cls, user, contact, parent=None):
        if contact.subscribed_to(user):
            return True
        if parent and parent.shared_with(contact):
            return True
        return False


class Self(Target):
    name = 'self'

    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': cls.name,
            'description': 'Only visible to myself',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return True

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return True

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post)


class Contact(Target):
    name = 'contact'

    @classmethod
    def json_target(cls, user, parent_post=None):
        if parent_post:
            user_list = cls._user_bothway_contacts_for_post(user, parent_post)
        else:
            user_list = cls._user_bothway_contacts(user)
        return {
            'name': cls.name,
            'description': 'Share with one friend',
            'targets': [json_contact(c) for c in user_list]
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool(cls._user_bothway_contacts(user))

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return bool(cls._user_bothway_contacts_for_post(user, parent_post))

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post)
        contact = [
            c for c in post.author.friends() if c.id == int(target)
        ]
        if contact:
            contact = contact[0]
        else:
            return
        if cls._contact_wants_to_hear_from_user(
            post.author,
            contact,
            post.parent
        ):
            post.share_with([contact])


class Group(Target):
    name = 'group'

    @classmethod
    def json_target(cls, user, parent_post=None):
        if parent_post:
            groups = (
                g for g in user.groups if
                cls._contacts_intersect_interested(
                    user,
                    cls._post_intersect_contacts(
                        parent_post,
                        [s.to_contact for s in g.subscriptions]
                    ),
                    parent_post
                )
            )
        else:
            groups = (
                g for g in user.groups if
                cls._contacts_intersect_interested(
                    user,
                    [s.to_contact for s in g.subscriptions]
                )
            )
        return {
            'name': cls.name,
            'description': 'Share with a group of friends',
            'targets': [json_group(g, user) for g in groups]
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool([
            g for g in user.groups if
            cls._contacts_intersect_interested(
                user,
                [s.to_contact for s in g.subscriptions]
            )
        ])

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        for g in user.groups:
            targets = cls._contacts_intersect_interested(
                user,
                [s.to_contact for s in g.subscriptions],
                parent_post
            )
            targets = cls._post_intersect_contacts(parent_post, targets)
            if targets:
                return True
        return False

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post)
        group = [
            g for g in post.author.groups if g.id == int(target)
        ]
        if group:
            group = group[0]
        else:
            return
        contacts = [
            s.to_contact for s in g.subscriptions
            if cls._contact_wants_to_hear_from_user(
                post.author,
                s.to_contact,
                post.parent
            )
        ]
        post.share_with(contacts)


class AllFriends(Target):
    name = 'all_friends'

    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': cls.name,
            'description': 'Share with all my friends',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool(cls._user_bothway_contacts(user))

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return bool(cls._post_intersect_contacts(
            parent_post,
            cls._user_bothway_contacts(user)
        ))

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post)
        contacts = [
            c for c in post.author.friends()
            if cls._contact_wants_to_hear_from_user(
                post.author,
                c,
                post.parent
            )
            and c.id != post.author_id
        ]
        post.share_with(contacts)


class ExistingViewers(Target):
    name = 'existing'

    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': cls.name,
            'description': 'Share with people who can see the item I am '
                           'replying to',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return False

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return True

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post)
        contacts = [
            s.contact for s in post.parent.shares
            if cls._contact_wants_to_hear_from_user(
                post.author,
                s.contact,
                post.parent
            )
            and s.contact_id != post.author_id
        ]
        post.share_with(contacts)


class Public(Target):
    name = 'wall'

    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': cls.name,
            'description': 'Show to everyone on my wall',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return True

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return parent_post.is_public()

    @classmethod
    def make_shares(cls, post, target):
        cls._make_self_share(post, True)

        post.implicit_share(post.author.followers())


target_list = (Self, Contact, Group, AllFriends, ExistingViewers, Public)
targets_by_name = dict((t.name, t) for t in target_list)
