import xml_stream
import requests
import colorix


def get_tree_from_url(url, name=None, dump=True):
    name = name or url
    if dump:
        print('Connecting to %s......' % name)
    tree = xml_stream.XMLTree(
        requests.get(url).iter_content()
    )
    if dump:
        colorix.recho('Result from %s:' % name)
    return tree


def print_certain_part(url, selector, text_fn, find_count_max=None, name=None, dump=True):
    print('\n'.join(
        text_fn(node)
        for node in
        get_tree_from_url(url, name=name, dump=dump).process(selector=selector, find_count_max=find_count_max)
    ))


def nice(source):
    return '\n'.join(node.repr_pretty() for node in xml_stream.XMLTree(source).process())


def test():
    print(nice(
        '<a target="_blank" href="https://github.com/"><i class="fa fa-github"></i>Github</a>'
        ' is <strong>awesome</strong>!'
    ))
    print_certain_part(
        'https://github.com/arrowrowe',
        'li.source',
        lambda node: 'Repo: %s (%s Starred)\nDesc: %s' % (
            colorix.fore(node.find('.repo-and-owner'), 'yellow'),
            colorix.fore(node.find('.stars'), 'cyan'),
            colorix.fore(node.find('.repo-description'), 'green')
        )
    )
    print_certain_part(
        'http://www.jwc.sjtu.edu.cn/rss/rss_notice.aspx?SubjectID=198015&TemplateID=221027',
        'item',
        lambda node: '%s (%s)' % (
            colorix.fore(node.title, 'cyan'),
            colorix.fore(node.pubDate, 'yellow')
        ),
        name='RSS SJTU',
        find_count_max=5
    )
    print_certain_part(
        'https://github.com/blog.atom',
        'entry',
        lambda node: '[%s] %s (%s)' % (
            colorix.fore(node.category, 'green'),
            colorix.fore(node.title, 'cyan'),
            colorix.fore(node.updated, 'yellow')
        ),
        name='RSS Github Blog',
        find_count_max=5
    )


if __name__ == '__main__':
    test()