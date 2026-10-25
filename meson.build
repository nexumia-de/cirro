project('cirro',
  version: '0.1.0',
  meson_version: '>= 1.0',
  license: 'AGPL-3.0-or-later',
)

app_id = 'io.github.suitably.Cirro'

python = import('python').find_installation('python3')
pythondir = python.get_install_dir()

python.install_sources(
  'cirro/__init__.py',
  'cirro/__main__.py',
  'cirro/colors.py',
  'cirro/legend.py',
  'cirro/main.py',
  'cirro/projection.py',
  'cirro/radar.py',
  'cirro/radar_layer.py',
  'cirro/source.py',
  'cirro/window.py',
  subdir: 'cirro',
)

conf = configuration_data()
conf.set('PYTHON', python.full_path())
conf.set('PYTHONDIR', get_option('prefix') / pythondir)
configure_file(
  input: 'data/cirro.in',
  output: 'cirro',
  configuration: conf,
  install: true,
  install_dir: get_option('bindir'),
  install_mode: 'rwxr-xr-x',
)

install_data('data' / app_id + '.desktop',
  install_dir: get_option('datadir') / 'applications')
install_data('data' / app_id + '.metainfo.xml',
  install_dir: get_option('datadir') / 'metainfo')
install_data('data/icons' / app_id + '.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps')

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('validate-desktop', desktop_file_validate,
    args: [meson.project_source_root() / 'data' / app_id + '.desktop'])
endif
appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-metainfo', appstreamcli,
    args: ['validate', '--no-net',
           meson.project_source_root() / 'data' / app_id + '.metainfo.xml'])
endif
