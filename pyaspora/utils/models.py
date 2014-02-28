import re


class TagParseMixin:
    @classmethod
    def name_is_valid(cls, name):
        if not name:
            return False

        if len(name) > 100:
            return False

        if re.search(r'[^a-z0-9_]', name):
            return False

        if '__' in name:
            return False

        if name.startswith('_'):
            return False

        if name.endswith('_'):
            return False

        return True

    @classmethod
    def parse_line(cls, line, create=True, **kwargs):
        tags = []
        for possible_tag in re.split('[,\s]+', line):
            tag = cls.get_by_name(possible_tag.lower(), create, **kwargs)
            if tag:
                tags.append(tag)
        return tags
