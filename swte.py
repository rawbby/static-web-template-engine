import os
import re
import shutil
import sys
import tempfile
import minify_html

pattern_config = re.compile(r'([a-z_]+)=([^\r\n]*)')
pattern_file = re.compile(r'<file [^>]*?src="([^"]*?)"[^>]*?>((?:(?!<file )[\W\w])*?)</file>')
pattern_hook = re.compile(r'<hook [^>]*?src="([^"]*?)"[^>]*?>((?:(?!<hook )[\W\w])*?)</hook>')
pattern_var = re.compile(r'\[\[([a-z_]+)]]')
pattern_ext_html = re.compile(r'[\W\w]*\.html')
pattern_ext_css = re.compile(r'[\W\w]*\.css')
pattern_ext_js = re.compile(r'[\W\w]*\.js')


def re_sub(pattern, dictionary, fn, text):
    n = 1
    while n:
        text, n = re.subn(pattern, lambda m: fn(dictionary, m, text), text, count=1)
    return text


def load_dictionary(template_directory):
    config_path = os.path.join(template_directory, '.config')
    dictionary = {}

    if os.path.isfile(config_path):
        with open(config_path, 'r') as config_content:
            for (key, value) in re.findall(pattern_config, config_content.read()):
                dictionary[key] = value

    return dictionary


def apply_file(dictionary, match, _):
    return dictionary[f"file://{match.group(1)}"]


def apply_hook(dictionary, match, text):
    loc = {}
    exec(dictionary[f"file://{match.group(1)}"], globals(), loc)
    return loc['generate'](text, match.group(2))


def apply_var(dictionary, match, _):
    return dictionary[match.group(1)]


def generate(template_directory, temporary_directory=None, dictionary=None):
    temporary_directory = temporary_directory or tempfile.mkdtemp()
    dictionary = dictionary or {'file://.config': '', 'file://index.html': ''}

    # Load directory content
    for file in os.listdir(template_directory):
        if os.path.isfile(os.path.join(template_directory, file)):
            with open(os.path.join(template_directory, file), 'r') as file_content:
                dictionary[f"file://{file}"] = file_content.read()

    # Update config variables
    for (key, value) in re.findall(pattern_config, dictionary['file://.config']):
        dictionary[key] = value

    # Get, fill and optimise index template
    index = dictionary['file://index.html']
    index = re_sub(pattern_file, dictionary, apply_file, index)
    index = re_sub(pattern_hook, dictionary, apply_hook, index)
    index = re_sub(pattern_var, dictionary, apply_var, index)
    index = minify_html.minify(index, minify_css=True, minify_js=True, do_not_minify_doctype=True, keep_html_and_head_opening_tags=True,
                               keep_closing_tags=True, ensure_spec_compliant_unquoted_attribute_values=True)

    # Write index
    with open(os.path.join(temporary_directory, 'index.html'), 'w') as index_file:
        index_file.write(index)

    # Recursively generate subdirectories
    for subdirectory in os.listdir(template_directory):
        if os.path.isdir(os.path.join(template_directory, subdirectory)):
            os.mkdir(os.path.join(temporary_directory, subdirectory))
            generate(os.path.join(template_directory, subdirectory), os.path.join(temporary_directory, subdirectory), dictionary)

    return temporary_directory


def main():
    template_directory = os.path.abspath(sys.argv[1])
    deploy_directory = os.path.abspath(sys.argv[2])

    generated_directory = generate(template_directory)
    shutil.rmtree(deploy_directory, ignore_errors=True)
    shutil.move(generated_directory, deploy_directory)


if __name__ == '__main__':
    main()
