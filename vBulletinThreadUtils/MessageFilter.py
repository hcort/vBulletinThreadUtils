class MessageFilter(object):
    """
        Interface for all kinds of message filtering criteria

        Every specialized class should implement the filter_message method
        that decides if the message is stored in the result collection

        usage:

        if filter_object and filter_object.filter_message(message):
            message_collection[message_id] = message
    """

    def filter_message(self, post_id: str, message: dict) -> bool:
        """
        :return: True if the message is valid according to filter
        """
        raise NotImplementedError("Should have implemented this")


class MessageFilterByAuthor(MessageFilter):

    def __init__(self, author):
        self.__author = author

    def filter_message(self, post_id: str, message: dict) -> bool:
        """
        :return: True if the message has been posted by certain author

            author is filtered by user name, not user id
        """
        if not self.__author:
            return True
        if self.__author == '@OP':
            return message.get('author', {}).get('is_op', '')
        else:
            return self.__author == message.get('author', {}).get('username', '')
