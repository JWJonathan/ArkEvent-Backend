from rest_framework.renderers import JSONRenderer

class CoreJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        status_code = renderer_context['response'].status_code

        response_dict = {
            "success": True if status_code < 400 else False,
            "data": data if status_code < 400 else None,
            "message": data.get('detail', '') if isinstance(data, dict) and status_code >= 400 else "",
        }

        if status_code >= 400 and isinstance(data, dict):
            response_dict['errors'] = data

        return super().render(response_dict, accepted_media_type, renderer_context)
