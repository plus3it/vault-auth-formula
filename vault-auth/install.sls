install_python_dependencies:
  pip.installed:
    - pkgs:
      - hvac
{%- if salt.grains.get('pythonversion')[0] | int == 3 %}
    - target: /usr/lib/python3.6/site-packages
{%- endif %}
    - reload_modules: True
    - ignore_installed: True
