import json
import logging
import requests

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.DoNothingAction import DoNothingAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction


logger = logging.getLogger(__name__)


class LlamaExtension(Extension):
    def __init__(self):
        super().__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())

    def get_llama_headers(self):
        headers = {}
        if self.preferences["llama_headers"]:
            for header in self.preferences["llama_headers"].split(","):
                header_key, header_value = header.split(":")
                headers[header_key.strip()] = header_value.strip()
        return headers

    def list_models(self):
        r = requests.get(
            self.preferences["llama_host"] + "api/v1/model",
            headers=self.get_llama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise LlamaException("Error connecting to llama.")

        model = response["result"]

        return [model]

    def generate(self, event):

        logger.info(event)
        data = {
            "prompt": self.preferences["llama_system_prompt"] + event["query"],
            "llama_max_context_length": self.preferences["llama_max_context_length"],
            "llama_max_length": self.preferences["llama_max_length"],
            "llama_rep_pen": self.preferences["llama_rep_pen"],
            "llama_rep_pen_range": self.preferences["llama_rep_pen_range"],
            "llama_rep_pen_slope": self.preferences["llama_rep_pen_slope"],
            "llama_temperature": self.preferences["llama_temperature"],
            "llama_top_k": self.preferences["llama_top_k"],
            "llama_top_p": self.preferences["llama_top_p"],
        }

        r = requests.post(
            self.preferences["llama_host"] + "api/v1/generate",
            data=json.dumps(data),
            headers=self.get_llama_headers(),
        )
        response = r.json()

        if r.status_code != 200:
            raise LlamaException("Error connecting to llama.")

        logger.debug(response)
        if "results" in response:
            if len(response["results"]) == 1:
                response = response["results"][0]["text"]

        return response


class ItemEnterEventListener(EventListener):
    def on_event(self, event, extension):
        # event is instance of ItemEnterEvent

        query = event.get_data()
        logger.debug(query)
        # do additional actions here...
        response = extension.generate(query)

        logger.debug(response)

        # you may want to return another list of results
        return RenderResultListAction(
            [
                ExtensionResultItem(
                    icon="images/llama.png",
                    name="Llama says..",
                    description=response,
                    on_enter=CopyToClipboardAction(response),
                )
            ]
        )


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        models = extension.list_models()
        query = event.get_query().replace(extension.preferences["llama_kw"] + " ", "")

        items = []

        for m in models:
            items.append(
                ExtensionResultItem(
                    icon="images/llama.png",
                    name="Ask " + m + "...",
                    description=query,
                    on_enter=ExtensionCustomAction(
                        {"query": query, "model": m}, keep_app_open=True
                    ),
                )
            )

        return RenderResultListAction(items)


class LlamaException(Exception):
    """Exception thrown when there was an error calling the llama API"""

    pass


if __name__ == "__main__":
    LlamaExtension().run()
