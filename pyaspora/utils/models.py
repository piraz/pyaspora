from __future__ import absolute_import

from re import search as re_search, split as re_split


class TagParseMixin:
    @classmethod
    def name_is_valid(cls, name):
        if not name:
            return False

        if len(name) > 100:
            return False

        if re_search(r'[^a-z0-9_]', name):
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
        seen = set()
        for possible_tag in re_split('[,\s]+', line):
            possible_tag = possible_tag.lower()

            if possible_tag in seen:
                continue
            else:
                seen.add(possible_tag)

            tag = cls.get_by_name(
                possible_tag,
                create=create,
                **kwargs
            )
            if tag:
                tags.append(tag)
        return tags
