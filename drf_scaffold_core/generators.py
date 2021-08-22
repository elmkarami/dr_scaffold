import inflect
from os import path, system
from drf_scaffold_core.scaffold_templates import model_templates, admin_templates, view_templates, serializer_templates, url_templates
from drf_scaffold_core import file_api

def pluralize(str):
    p = inflect.engine()
    return p.plural(str)

def wipe_files(file_paths):
    for f in file_paths:
        file_api.wipe_file_content(f)

def create_files(file_paths):
    for f in file_paths:
        file_api.create_file(f)

class Generator(object):

    def __init__(self, appdir, model_name, fields):
      self.appdir = appdir
      self.MAIN_DIR = './'
      self.app_name = appdir
      if len(appdir.split('/'))>= 2:
        self.MAIN_DIR = appdir.split("/", maxsplit=1)[0]
        self.app_name = appdir.split("/", maxsplit=1)[1]
      self.model_name = model_name
      self.fields = fields

    def generate(self):
      self.generate_app()
      self.generate_models()
      self.register_models_to_admin()
      # self.generate_serializers()
      # self.generate_views()
      # self.generate_urls()

    def setup_files(self):
      extra_files = (f"{self.appdir}/serializers.py", f"{self.appdir}/urls.py" )
      original_files = (f"{self.appdir}/models.py", f"{self.appdir}/admin.py", f"{self.appdir}/views.py")
      all_files = extra_files + original_files
      setup_imports = (serializer_templates.SETUP, url_templates.SETUP, model_templates.SETUP, admin_templates.SETUP, view_templates.SETUP)
      create_files(extra_files)
      wipe_files(all_files)
      self.add_setup_imports(all_files, setup_imports)

    def add_setup_imports(self, file_paths, imports):
      for i, f in enumerate(file_paths):
        file_api.set_file_content(f, imports[i])

    def generate_app(self):
      if not path.exists('%s' % (self.appdir)):
        system(f'python manage.py startapp {self.app_name}')
        system(f'mv {self.app_name} {self.appdir}')
        self.setup_files()
      else:
        print(f"App does already exist at {self.appdir}")

    def get_model_string(self):
      fields_list = self.get_fields_template_list(self.fields)
      fields_string = ''.join(field for field in fields_list)
      verbose_model = pluralize(self.model_name).capitalize()
      model_string = model_templates.MODEL % (self.model_name, fields_string, verbose_model)
      return model_string

    def generate_models(self):
      models_file = f"{self.appdir}/models.py"
      model_class_head = f'class {self.model_name}'
      if file_api.is_present_in_file(models_file, model_class_head):
        return 
      model_string = self.get_model_string()
      file_api.append_file_content(models_file, model_string)

    def rewrite_component_file(self, file_path, head, body):
      with open(file_path, 'r+') as file:
        file_content = ''.join(line for line in file.readlines())
        if file_path == f"{self.appdir}/urls.py":
          file_content = file_content.replace(url_templates.URL_PATTERNS,"")
        new_content = head + file_content + body + "\n"
        file.seek(0)
        file.write(new_content)

    def get_fields_template_list(self, fields):
      actual_fields = list()
      for field in fields:
        new_field = self.select_field_template(field)
        if new_field:
          actual_fields.append(new_field)
      return actual_fields

    def class_exist(self, component, file, model): 
      for line in file.readlines():
        if component == 'view':
          if f'class {model}ViewSet' in line:
            print(f'ViewSet already exists at {self.appdir}/views.py')
            return True   
        elif component == 'serializer':
          if f'class {model}Serializer' in line:
            print(f'Serializer already exists at {self.appdir}/serializers.py')
            return True
        elif component == 'url':
          if f'{model}ViewSet)' in line:
            print(f'Url already exists at {self.appdir}/urls.py')
            return True           
      return False

    def select_field_template(self, field):
      field_name = field.split(':')[0]
      field_type = field.split(':')[1].lower()
      return model_templates.FIELD_TYPES[field_type] % dict(name= field_name, foreign = field.split(':')[2] if (field_type == 'foreignkey') else '')

    def is_imported(self, path, model):
      file = open(path, 'r')
      for line in file.readlines():
        if f'import {model}' in line:
          return True
      return False

    def register_models_to_admin(self):
      admin_file = f"{self.appdir}/admin.py"
      admin_register_head = f'@admin.register({self.model_name})'
      if file_api.is_present_in_file(admin_file, admin_register_head):
        return 
      app_path = self.appdir.replace("/", ".")
      model_register_template = admin_templates.REGISTER % {'model': self.model_name}
      model_import_template = admin_templates.MODEL_IMPORT % {'app': app_path, 'model': self.model_name}
      file_api.wrap_file_content(admin_file, model_import_template, model_register_template)

    def generate_views(self):
      view_file = open(f"{self.appdir}/views.py", 'r')
      if self.class_exist('view', view_file, self.model_name):
        return 
      viewset_template = view_templates.VIEWSET % {'model': self.model_name}
      model_import_template = view_templates.MODEL_IMPORT % {'app': self.appdir.replace("/", "."), 'model': self.model_name}
      serializer_import_template= view_templates.SERIALIZER_IMPORT % {'app': self.appdir.replace("/", "."), 'model': self.model_name}
      imports = model_import_template+serializer_import_template
      self.rewrite_component_file(f"{self.appdir}/views.py", imports,viewset_template)
      return print(f"🚀 {self.appdir}/views.py have been successfully updated")

    def generate_serializers(self):
      serializer_file = open(f"{self.appdir}/serializers.py", 'r')
      if self.class_exist('serializer', serializer_file, self.model_name):
        return 
      serializer_template = serializer_templates.SERIALIZER % {'model': self.model_name}
      model_import_template = serializer_templates.MODEL_IMPORT % {'app': self.appdir.replace("/", "."), 'model': self.model_name}
      self.rewrite_component_file(f"{self.appdir}/serializers.py", model_import_template,serializer_template)
      return print(f"🚀 {self.appdir}/views.py have been successfully updated")

    def generate_urls(self):
      urls_file = open(f"{self.appdir}/urls.py", 'r')
      if self.class_exist('url', urls_file, self.model_name):
        return 
      url_template = url_templates.URL % {'model': self.model_name, 'path': pluralize(self.model_name.lower())} + url_templates.URL_PATTERNS
      model_import_template = url_templates.MODEL_IMPORT % {'app': self.appdir.replace("/", "."), 'model': self.model_name}
      self.rewrite_component_file(f"{self.appdir}/urls.py", model_import_template,url_template)
      return print(f"🚀 {self.appdir}/urls.py have been successfully updated")