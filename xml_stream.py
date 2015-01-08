import re
import types
import colorix


class Node:
    """
    An element in the XML tree.
    Note that text will be considered as an element without name.
    """
    def __init__(self, name='', content='', raw_attr=None, re_attr=None, charset='utf-8'):
        self.charset = charset
        self.name = name.encode(self.charset)
        self.content = content
        self._attr_dict = {}
        if raw_attr:
            self.add_raw_attr(raw_attr, re_attr)
        self.parent = None
        self.next = None
        self.first_child = None
        self.last_child = None

    def add_raw_attr(self, raw_attr, re_attr):
        result = re.search(re_attr, raw_attr)
        while result is not None:
            self.add_attr(result.group('key'), result.group('value'))
            raw_attr = raw_attr[result.end():]
            result = re.search(re_attr, raw_attr)

    def get_raw_attr(self):
        return ''.join(' %s="%s"' % (k, v if type(v) is str else ' '.join(v)) for k, v in self._attr_dict.items())

    def get_raw_attr_pretty(self, color_key='green', color_value='yellow'):
        return ''.join(
            ' %s="%s"' % (colorix.fore(k, color_key), colorix.fore(v if type(v) is str else ' '.join(v), color_value))
            for k, v in self._attr_dict.items()
        )

    def add_attr(self, key, value):
        if key == 'class':
            self._attr_dict[key] = value.split()
        else:
            self._attr_dict[key] = value

    def add_content(self, raw_content):
        content = raw_content.strip()
        if content:
            self.append(Node(content=content))

    def __repr__(self):
        return \
            (
                (
                    '<' + self.name + self.get_raw_attr() + '>'
                ) if self.name else ''
            ) + \
            self.content.encode(self.charset) + \
            ''.join(repr(node) for node in self.children()) + \
            (
                ('</%s>' % self.name) if self.name else ''
            )

    def repr_pretty(self, prefix='', prefix_one='    ', color_name='red', color_key='green', color_value='yellow',
                    color_text='cyan'):
        return \
            (
                (
                    prefix + '<' + colorix.fore(self.name, color_name) +
                    self.get_raw_attr_pretty(color_key=color_key, color_value=color_value) +
                    '>'
                ) if self.name else ''
            ) + \
            (
                ((prefix + colorix.back(self.content.encode(self.charset), color_text)) if self.content else '') +
                ('\n' if self.first_child is not None else '') +
                '\n'.join(
                    node.repr_pretty(
                        prefix=prefix + prefix_one, prefix_one=prefix_one,
                        color_name=color_name, color_key=color_key, color_value=color_value, color_text=color_text
                    ) for node in self.children()
                )
            ) + \
            (
                (
                    (('\n' + prefix) if (self.content != '' or self.first_child is not None) else '') +
                    ('</%s>' % colorix.fore(self.name, color_name))
                ) if self.name else ''
            )

    def __str__(self):
        """
        Get visible content of the node.
        :return: string
        :todo: Support comment and more.
        """
        return self.content + ''.join(str(node) for node in self.children())

    def append(self, child):
        """
        Append a child for the node. The parent will be returned for chain method.
        :param child: the node to be appended
        :return: the parent node
        """
        child.parent = self
        if self.first_child is None:
            self.first_child = child
            self.last_child = child
        else:
            self.last_child.next = child
            self.last_child = child
        return self

    def children(self):
        """
        Produce all direct children of the node, including text, which will be produced as elements without names.
        This function is a generator.
        """
        node = self.first_child
        while node is not None:
            yield node
            node = node.next

    def children_recursive(self):
        """
        Produce all children and great-children (in short, all recursive children) of the node.
        This function is a generator.
        """
        for node in self.children():
            yield node
            for sub_node in node.children_recursive():
                yield sub_node

    def findall(self, selector):
        """
        Find all satisfying nodes from all recursive children.
        This function is a generator.
        """
        selector = get_selector(selector)
        if selector is None:
            raise StopIteration
        for node in self.children_recursive():
            if selector(node):
                yield node

    def find(self, selector):
        """
        Find the first satisfying recursive child.
        """
        for node in self.findall(selector):
            return node
        return None

    def __getattr__(self, attr):
        """
        Get attribute or child of the node.
        It's like `href` of `a` in `<a href="https://github.com/">Github</a>`,
        or `link` of `item` in '<item><link>https://github.com/arrowrowe</link></item>'.
        :return: string or node
        """
        if attr in self._attr_dict:
            return self._attr_dict[attr]
        else:
            node = self.find(selector=attr)
            return '' if node is None else node

    def attr(self, attr):
        """
        Get some name-protected attributes of the node, like `name`, `id`, `class` and so on.
        :param attr: string
        :return: string or node
        """
        return self.__getattr__(attr)


class XMLTreeOption:
    """
    Define the behavior for a XML tree, which means the process can be costumed.
    """
    def __init__(
            self,
            charset='utf-8',
            short=r'<([\w:]+)( .*)?/>',
            prefix=r'<([\w:]+)( .*)?>',
            suffix=r'</([\w:]+)>',
            comment=r'<\?.*?\?>|<\!.*?>',
            attr=r'(?P<key>\w+)=(?P<q>"?)(?P<value>.*?)(?P=q)(?= |$)',
            pure_text=r'<!\[CDATA\[(.+?)\]\]>',
            shorts=('link', 'input', 'img', 'meta', 'br', 'hr')
    ):
        self.charset = charset
        self.IS_NONE = -1
        self.IS_SHORT = 0
        self.IS_PREFIX = 1
        self.IS_SUFFIX = 2
        self.patterns = [short, prefix, suffix]
        self.pattern_comment = comment
        self.pattern_attr = attr
        self.pattern_pure_text = pure_text
        self.shorts = shorts

    def exam(self, tail):
        """
        Decide if a string contains some particular content.
        :param tail: string
        :return: a tuple of result-type-constant and RE.MatchObject (or None)
        """
        for pattern_index, pattern in enumerate(self.patterns):
            r = re.search(pattern, tail, re.DOTALL)
            if r is not None:
                return pattern_index, r
        return self.IS_NONE, None


class XMLTree:
    def __init__(self, stream, option=None):
        self.stream = stream
        self.option = XMLTreeOption() if option is None else option
        self.tail = ''
        self.stack = [Node('xml', charset=self.option.charset)]
        self.tmp = []
        self.current_line = -1
        self.current_index = -1
        self.force_stop = False

    def process_one(self, item_count_max=0, selector=None, find_count_max=0):
        for node in self.process(item_count_max=item_count_max, selector=selector, find_count_max=find_count_max):
            return node

    def process(self, item_count_max=0, selector=None, find_count_max=0):
        self.current_line = 0
        self.current_index = 0
        self.force_stop = False
        item_count = 0
        find_count = 0
        selector = get_selector(selector)
        for e in self.stream:
            if e == '\n':
                self.current_index = 0
                self.current_line += 1
            else:
                self.current_index += 1
            self.tail += e
            tail_type, r = self.option.exam(self.tail)
            if tail_type == self.option.IS_NONE:
                pass
            elif tail_type == self.option.IS_SHORT:
                self.tail = self.tail[:r.start()]
                tag_name = r.group(1)
                self.tmp.append(
                    self.stack[-1].append(
                        Node(tag_name,
                             raw_attr=r.group(2), re_attr=self.option.pattern_attr, charset=self.option.charset)
                    ).last_child
                )
            elif tail_type == self.option.IS_PREFIX:
                tag_name = r.group(1)
                last_node = self.stack[-1]
                if last_node.name.lower() in self.option.shorts:
                    self.stack.pop()
                    self.tmp.append(last_node)
                    last_node = self.stack[-1]
                last_node.add_content(self.tail[:r.start()])
                self.tail = ''
                self.stack.append(
                    last_node.append(
                        Node(tag_name, raw_attr=r.group(2), re_attr=self.option.pattern_attr,
                             charset=self.option.charset)
                    ).last_child
                )
            elif tail_type == self.option.IS_SUFFIX:
                tag_name = r.group(1)
                last_node = self.stack.pop()
                if last_node.name.lower() != tag_name.lower():
                    if last_node.name.lower() in self.option.shorts:
                        last_node = self.stack.pop()
                    else:
                        raise Exception(
                            (
                                colorix.colorama.Style.BRIGHT +
                                '\nError occurs at line %s, column %s.'
                                ' Tag does not match, "%s" expected, "%s" found.'
                                ' Investigate XMLTree object for details. '
                                % (
                                    colorix.fore(self.current_line + 1, 'green'),
                                    colorix.fore(self.current_index + 1, 'green'),
                                    colorix.fore(last_node.name, 'red'),
                                    colorix.fore(tag_name, 'red')
                                )
                            ) +
                            (
                                '\nStack: [%s]' % ', '.join(node.name for node in self.stack)
                            ) +
                            (
                                '\nProcessing text: ' + colorix.back(self.tail, 'cyan')
                            ) +
                            '\nLast node:\n' + last_node.repr_pretty()
                        )
                last_node.add_content(self.tail[:r.start()])
                self.tail = ''
                self.tmp.append(last_node)
            for n in self.tmp:
                if selector is not None and selector(n):
                    yield n
                    find_count += 1
                    if 0 < find_count_max <= find_count:
                        raise StopIteration
                item_count += 1
                if 0 < item_count_max <= item_count:
                    self.force_stop = True
                    break
            self.tmp = []
            if self.force_stop:
                break
        if self.tail:
            self.stack[-1].add_content(self.tail)
            self.tail = ''
        if selector is None:
            for n in self.stack[0].children():
                yield n


def get_selector(raw_selector):
    """
    Get lambda-selector or None (or simply 'selector' in short) from any type of raw-selector.
    :param raw_selector: any type
    :return: selector(a function or None)
    """
    if isinstance(raw_selector, types.FunctionType):
        return raw_selector
    elif isinstance(raw_selector, types.StringType):
        return get_selector_from_str(raw_selector)
    else:
        return None


def get_selector_from_str(raw_selector):
    """
    Get selector from string.
    :param raw_selector: string
    :return: selector
    """
    selectors = []
    for raw_selector_split in raw_selector.split(','):
        s = get_selector_from_split(raw_selector_split)
        if s is not None:
            selectors.append(s)
    if len(selectors) == 0:
        return None
    else:
        return lambda n: selectors_bool(selectors, n, True)


def selectors_bool(selectors, node, mode=True):
    """
    Verify a node by the provided selectors in or-mode or and-mode.
    :param selectors: an array of functions to verify the node
    :param node: the node to be verified
    :param mode: or-mode(True), and-mode(False)
    :return: bool
    """
    for selector in selectors:
        if selector(node) == mode:
            return mode
    return not mode


def get_selector_from_split(raw_selector):
    """
    Get selector from string without ','.
    :param raw_selector: string without ','
    :return: selector
    :todo: support ' ' and '>'
    """
    return get_selector_from_sym(raw_selector)


def get_selector_from_sym(raw_selector):
    """
    Get selector from string without ' ' or '>'.
    :param raw_selector: string without ' ' or '>'
    :return: selector
    """
    selectors = []
    tail = ''
    for e in raw_selector:
        if e in ('#', '.') and tail:
            s = get_one_selector_from_str(tail)
            tail = ''
            if s is not None:
                selectors.append(s)
        tail += e
    if tail:
        s = get_one_selector_from_str(tail)
        if s is not None:
            selectors.append(s)
    if len(selectors) == 0:
        return None
    else:
        return lambda n: selectors_bool(selectors, n, False)


def get_one_selector_from_str(raw_selector):
    """
    Get selector from a 'simple' string.
    :param raw_selector: string like 'img' or '#nav' or '.col-lg-12'
    :return: function
    """
    raw_selector = raw_selector.strip()
    mode = raw_selector[:1]
    de = raw_selector[1:]
    if mode == '#':
        return lambda n: n.attr('id') == de
    elif mode == '.':
        return lambda n: de in n.attr('class')
    else:
        return lambda n: n.name == raw_selector