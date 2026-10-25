project('cirro',
  version: '0.1.0',
  meson_version: '>= 1.0',
  license: 'AGPL-3.0-or-later',
)

base_id = 'de.nexumia.Cirro'
# Nightly app next to the stable one (docs/release-channels.md).
nightly = get_option('profile') == 'development'
app_id = nightly ? base_id + '.Devel' : base_id

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

config = configuration_data()
config.set('APP_ID', app_id)
config.set('BUILD_LABEL', get_option('build_label'))
configure_file(
  input: 'cirro/config.py.in',
  output: 'config.py',
  configuration: config,
  install: true,
  install_dir: pythondir / 'cirro',
)

if nightly
  variant = [python, files('build-aux/nightly.py'), '@INPUT@', '@OUTPUT@', app_id]
  desktop = configure_file(input: 'data' / base_id + '.desktop',
    output: app_id + '.desktop', command: variant)
  metainfo = configure_file(input: 'data' / base_id + '.metainfo.xml',
    output: app_id + '.metainfo.xml', command: variant)
else
  desktop = files('data' / base_id + '.desktop')
  metainfo = files('data' / base_id + '.metainfo.xml')
endif
install_data(desktop, install_dir: get_option('datadir') / 'applications')
install_data(metainfo, install_dir: get_option('datadir') / 'metainfo')
install_data('data/icons' / base_id + '.svg',
  install_dir: get_option('datadir') / 'icons/hicolor/scalable/apps',
  rename: app_id + '.svg')

desktop_file_validate = find_program('desktop-file-validate', required: false)
if desktop_file_validate.found()
  test('validate-desktop', desktop_file_validate, args: [desktop])
endif
appstreamcli = find_program('appstreamcli', required: false)
if appstreamcli.found()
  test('validate-metainfo', appstreamcli,
    args: ['validate', '--no-net', metainfo])
endif
