from html2bbcode import parse_children_in_node


class MessageProcessor(object):
    """
        Interface for all kinds of message processor

        Every specialized class should implement the process_message method
        that reads a message and does some work on it
    """

    def process_message(self, post_id: str, message: dict):
        raise NotImplementedError("Should have implemented this")


class MessageHTMLToText(MessageProcessor):

    def process_message(self, post_id: str, message: dict):
        return message['HTML'].prettify(formatter="minimal") if message.get('HTML', None) else ''


class MessageHTMLToBBCode(MessageProcessor):

    def process_message(self, post_id: str, message: dict):
        return parse_children_in_node(message['HTML']) if message.get('HTML', None) else ''
