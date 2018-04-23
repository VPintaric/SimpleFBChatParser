import re
import argparse

from html.parser import HTMLParser

class FbMessage():
    def __init__(self):
        self.user_name = ""
        self.content = ""
        self.datetime = ""
        self.n_reactions = 0

class FbChatParticipantData():
    def __init__(self, name):
        self.name = name
        self.n_msgs = 0
        self.n_words = 0

        self.msgs_per_weekday = 7 * [0]
        self.msgs_per_hours = 24 * [0]
        self.words_per_weekday = 7 * [0]
        self.words_per_hour = 24 * [0]

class FbChatHTMLParser(HTMLParser):

    def __init__(self):
        HTMLParser.__init__(self)

        self.in_convo_tags = False
        self.in_msg_tags = False
        self.in_msg_hdr_tags = False
        self.in_reaction_list_tags = False
        self.in_reaction_tags = False
        self.in_user_tags = False
        self.in_meta_tags = False
        self.in_p_tags = False

        self.cur_msg = None
        self.user_data = {}

        self.most_reacted_msgs = []
        self.all_participants = FbChatParticipantData("__ALL__")

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if ("class", "thread") in attrs:
                self.in_convo_tags = True
            elif self.in_convo_tags and ("class", "message") in attrs:
                self.finalize_last_message()
                self.cur_msg = FbMessage()
                self.in_msg_tags = True
            elif self.in_msg_tags and ("class", "message_header") in attrs:
                self.in_msg_hdr_tags = True
        elif tag == "span" and self.in_msg_hdr_tags:
            if ("class", "user") in attrs:
                self.in_user_tags = True
            if ("class", "meta") in attrs:
                self.in_meta_tags = True
        elif tag == "ul" and self.in_convo_tags:
            self.in_reaction_list_tags = True
        elif tag == "li" and self.in_reaction_list_tags:
            self.in_reaction_tags = True
        elif tag == "p" and self.in_convo_tags:
            self.in_p_tags = True

    def handle_endtag(self, tag):
        if tag == "div":
            if self.in_msg_hdr_tags:
                self.in_msg_hdr_tags = False
            elif self.in_msg_tags:
                self.in_msg_tags = False
            elif self.in_convo_tags:
                self.in_convo_tags = False
        elif tag == "span":
            if self.in_user_tags:
                self.in_user_tags = False
            elif self.in_meta_tags:
                self.in_meta_tags = False
        elif tag == "ul" and self.in_reaction_list_tags:
            self.in_reaction_list_tags = False
        elif tag == "li" and self.in_reaction_tags:
            self.in_reaction_tags = False
            self.cur_msg.n_reactions += 1
        elif tag == "p" and self.in_p_tags:
            self.in_p_tags = False

    def handle_data(self, data):
        if self.in_user_tags:
            self.cur_msg.user_name = data
        elif self.in_meta_tags:
            self.cur_msg.datetime = data
        elif self.in_p_tags:
            self.cur_msg.content += data + "\n"

    def weekday_to_idx(self, weekday):
        return {
            "Monday" : 0,
            "Tuesday" : 1,
            "Wednesday" : 2,
            "Thursday" : 3,
            "Friday" : 4,
            "Saturday" : 5,
            "Sunday" : 6
        }.get(weekday, "Well fuck me")

    def get_msg_time_info(self, msg):
        regex = "(\w*), (\w* \w* \w*) at (\d*)"
        m = re.match(regex, msg.datetime)
        return m.group(2), self.weekday_to_idx(m.group(1)), int(m.group(3))

    def count_words(self, msg):
        return len(msg.content.split())

    def finalize_last_message(self):
        if self.cur_msg:
            if(self.cur_msg.n_reactions > 0):
                self.most_reacted_msgs.append(self.cur_msg)

            date, weekday, hour = self.get_msg_time_info(self.cur_msg)
            n_words = self.count_words(self.cur_msg)

            self.all_participants.n_msgs += 1
            self.all_participants.msgs_per_hours[hour] += 1
            self.all_participants.msgs_per_weekday[weekday] += 1
            self.all_participants.n_words += n_words
            self.all_participants.words_per_hour[hour] += n_words
            self.all_participants.words_per_weekday[weekday] += n_words

            user = self.user_data.get(self.cur_msg.user_name)
            if user is None:
                user = FbChatParticipantData(self.cur_msg.user_name)
                self.user_data[self.cur_msg.user_name] = user

            user.n_msgs += 1
            user.msgs_per_hours[hour] += 1
            user.msgs_per_weekday[weekday] += 1
            user.n_words += n_words
            user.words_per_hour[hour] += n_words
            user.words_per_weekday[weekday] += n_words

def main():
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("input_file", type=str)
    arg_parser.add_argument("stats_file", type=str, nargs="?", default="stats.txt")
    arg_parser.add_argument("messages_file", type=str, nargs="?", default="messages.txt")
    args = arg_parser.parse_args()

    with open(args.input_file, "r") as f:
        content = f.read()
        html_parser = FbChatHTMLParser()
        html_parser.feed(content)

        with open(args.stats_file, "w") as stats_file, open(args.messages_file, "w") as msgs_file:
            html_parser.most_reacted_msgs.sort(key=lambda x: x.n_reactions, reverse=True)

            msgs_file.write("Most reacted to messages:\n\n")
            for msg in html_parser.most_reacted_msgs:
                msgs_file.write("User: " + msg.user_name + "\n")
                msgs_file.write("Date: " + msg.datetime + "\n")
                msgs_file.write("Content: " + msg.content + "\n\n")

            stats_file.write("Total number of messages: " + str(html_parser.all_participants.n_msgs) + "\n")
            stats_file.write("Total number of words: " + str(html_parser.all_participants.n_words) + "\n")
            stats_file.write("Total number of messages over a week (cumulative):\n")
            stats_file.write(str(html_parser.all_participants.msgs_per_weekday) + "\n")
            stats_file.write("Total number of words over a week (cumulative):\n")
            stats_file.write(str(html_parser.all_participants.words_per_weekday) + "\n")
            stats_file.write("Total number of messages over a day (cumulative):\n")
            stats_file.write(str(html_parser.all_participants.msgs_per_hours) + "\n")
            stats_file.write("Total number of words over a day (cumulative):\n")
            stats_file.write(str(html_parser.all_participants.words_per_hour) + "\n\n")

            stats_file.write("__Statistics per participant__\n\n")

            users = []
            for _, user in html_parser.user_data.items():
                users.append(user)
            users.sort(key=lambda x: x.n_msgs, reverse=True)

            for user in users:
                stats_file.write("__" + user.name + "__\n")
                stats_file.write("Total number of messages: " + str(user.n_msgs) + "\n")
                stats_file.write("Total number of words: " + str(user.n_words) + "\n")
                stats_file.write("Total number of messages over a week (cumulative):\n")
                stats_file.write(str(user.msgs_per_weekday) + "\n")
                stats_file.write("Total number of words over a week (cumulative):\n")
                stats_file.write(str(user.words_per_weekday) + "\n")
                stats_file.write("Total number of messages over a day (cumulative):\n")
                stats_file.write(str(user.msgs_per_hours) + "\n")
                stats_file.write("Total number of words over a day (cumulative):\n")
                stats_file.write(str(user.words_per_hour) + "\n\n")


if __name__ == '__main__':
    main()