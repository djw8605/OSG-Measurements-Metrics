
import cherrypy

from pkg_resources import resource_stream, resource_filename
from Cheetah.Template import Template as CTemplate

from graphtool.base.xml_config import XmlConfig

class Template(XmlConfig):

    def getTemplateFilename(self, template):
        template_name = template.replace(".", "_").replace("-", "_") + "_filename"
        if not hasattr(self, template_name):
            filename = resource_filename("gratia.templates", template)
            setattr(self, template_name, filename)
        return getattr(self, template_name)

    def defaultData(self, data):
        base_url = self.metadata.get('base_url', '')
        static_site_url = self.metadata.get('static_site_url', '')
        data['base_url'] = base_url
        data['static_site_url'] = static_site_url

    def plain_template(self, name=None, content_type='text/html'):
        template_fp = resource_stream("gratia.templates", name)
        tclass = CTemplate.compile(source=template_fp.read())
        def template_decorator(func):
            def func_wrapper(*args, **kw):
                data = func(*args, **kw)
                self.defaultData(data)
                cherrypy.response.headers['Content-Type'] = content_type
                return str(tclass(namespaces=[data]))
            func_wrapper.exposed = True
            return func_wrapper
        return template_decorator

    def template(self, name=None):
        main_filename = resource_filename("gratia.templates", name)
        template_fp = resource_stream("gratia.templates", 'yui_main.tmpl')
        tclass = CTemplate.compile(source=template_fp.read())
        def template_decorator(func):
            def func_wrapper(*args, **kw):
                data = func(*args, **kw)
                self.defaultData(data)
                data['main_tmpl'] = main_filename
                return str(tclass(namespaces=[data]))
            func_wrapper.exposed = True
            return func_wrapper
        return template_decorator

