class Target:
    @classmethod
    def _post_intersect_contacts(cls, post, contacts):
        parent_shared_with = set(s.contact_id for s in post.shares)
        return [c for c in contacts if c.id in parent_shared_with]

    @classmethod
    def _contacts_intersect_interested(cls, user, contacts):
        return [c for c in contacts if c.subscribed_to(user)]


class Self(Target):
    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': 'self',
            'description': 'Only visible to myself',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return True

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return True


class Contact(Target):
    @classmethod
    def _user_bothway_contacts(cls, user):
        return cls._contacts_intersect_interested(user, user.contact.friends())

    @classmethod
    def _user_bothway_contacts_for_post(cls, user, post):
        return cls._post_intersect_contacts(
            post,
            cls._user_bothway_contacts(user)
        )

    @classmethod
    def json_target(cls, user, parent_post=None):
        if parent_post:
            user_list = cls._user_bothway_contacts_for_post(user, parent_post)
        else:
            user_list = cls._user_bothway_contacts(user)
        return {
            'name': 'contact',
            'description': 'Share with one friend',
            'targets': [json_contact(c) for c in user_list]
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool(cls._user_bothway_contacts(user))

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return bool(cls._user_bothway_contacts_for_post(user, post))


class Group(Target):
    @classmethod
    def json_target(cls, user, parent_post=None):
        if parent_post:
            groups = (
                g for g in user.groups if
                cls._contacts_intersect_interested(
                    user,
                    cls._post_intersect_contacts(parent_post, g.contacts)
                )
            )
        else:
            groups = (
                g for g in user.groups() if
                cls._contacts_intersect_interested(user, g.contacts)
            )
        return {
            'name': 'group',
            'description': 'Share with a group of friends',
            'targets': [json_group(g, user) for g in groups]
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool([
            g for g in user.groups() if
            cls._contacts_intersect_interested(user, g.contacts)
        ])

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        for g in user.groups():
            targets = cls._contacts_intersect_interested(user, g.contacts)
            targets = cls._post_intersect_contacts(parent_post, targets)
            if targets:
                return True
        return False


class AllFriends(Target):
    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': 'all_friends',
            'description': 'Share with all my friends',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return bool(cls._user_bothway_contacts(user))

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return bool(cls._post_intersect_contacts(
            post,
            cls._user_bothway_contacts(user)
        ))


class ExistingViewers(Target):
    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': 'existing',
            'description': 'People who can see the item I am replying to',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return False

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return True


class Public(Target):
    @classmethod
    def json_target(cls, user, parent_post=None):
        return {
            'name': 'wall',
            'description': 'Show to everyone on my wall',
            'targets': None
        }

    @classmethod
    def permitted_for_new(cls, user):
        return True

    @classmethod
    def permitted_for_reply(cls, user, parent_post):
        return parent_post.shared_with(parent_post.author).public


target_list = (Self, Contact, Group, AllFriends, ExistingViewers, Public)
