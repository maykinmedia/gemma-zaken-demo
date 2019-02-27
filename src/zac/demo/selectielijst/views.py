from django.views.generic import TemplateView

from zds_client import Client

from ..mixins import ZACViewMixin


class SelectieLijstProcestypenView(ZACViewMixin, TemplateView):
    template_name = 'demo/selectielijst/procestype_list.html'
    title = 'Selectielijst'
    subtitle = 'Procestypen/resultaten ter ondersteuning van ZTC'

    def _pre_dispatch(self, request, *args, **kwargs):
        self.vrl_client = Client('vrl', base_path='/referentielijsten/api/v1/')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        procestypen = self.vrl_client.list('procestype')

        context['rows'] = procestypen

        return context
