# -*- coding: UTF-8
import re
import logging

log = logging.getLogger(__name__)

### Matchers ##################################################################

class BaseMatcher(object):
    pass


class RegexpMatcher(BaseMatcher):

    def __init__(self, reg_string, flags=re.IGNORECASE):
        log.debug((reg_string, flags))
        self.regexp = re.compile(reg_string, flags=flags)

    def matches(self, string):
        return self.regexp.search(string)


### Helpers ###################################################################

def get_matcher(args, pattern):
    if args.regexp is True:
        return RegexpMatcher(pattern)
    else:
        return None
