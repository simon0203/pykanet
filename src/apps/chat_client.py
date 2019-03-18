from network_interface import NetworkInterface
from network_message import NetworkMessage

from kivy.uix.boxlayout import BoxLayout

from kivy.uix.screenmanager import Screen, NoTransition
from kivy.properties import StringProperty
from kivy.lang import Builder

from widgets.scrollable_label import ScrollableLabel
from widgets.shift_enter_textinput import ShiftEnterTextInput

from kivy.uix.scrollview import ScrollView
from kivy.uix.label import Label
from kivy.properties import StringProperty, ListProperty

from datetime import datetime
from dateutil import tz

from user_utils import MainUser

def convert_utc_to_local(utc_time):
    from_zone = tz.tzutc()
    to_zone = tz.tzlocal()
    utc = datetime.strptime(utc_time, '%Y-%m-%d %H:%M:%S')
    utc = utc.replace(tzinfo=from_zone)
    local = utc.astimezone(to_zone)
    return local.strftime('%Y-%m-%d, %H:%M:%S')

#for regular expressions
import re

#format the links in some text string, with the markup language of kivy
#TODO : code redundancy with ScrollableLabel
def format_links(text_str):
    #use a regular expression to add kivy color and ref markup around web addresses
    text_str = re.sub(r'(https?:\S*)', r'[color=0000ff][u][ref=\1]\1[/ref][/u][/color]', text_str, flags=re.MULTILINE)
    return text_str

    
Builder.load_string('''
<CustomLabel>:
    size_hint_y: None
    size_hint_x: 0.8
    height: self.texture_size[1]
    text_size: self.width, None
    padding: [7, 7]
    markup:True
    on_ref_press: root.link_clicked(args[1])
    canvas.before:
        Color:
            rgba: root.bcolor
        RoundedRectangle:
            pos: self.pos
            size: self.size
''')

#default text to None, default background to white
class CustomLabel(Label):
    
    #add an event triggered when a link other than http link is clicked
    __events__ = Label.__events__ + ['on_link_clicked']
    
    bcolor = ListProperty([1,1,1,1])
    
    def link_clicked(self, link):
        if link.startswith("http"):
            import webbrowser
            webbrowser.open(link)
        else:
            self.dispatch('on_link_clicked', link)

    def on_link_clicked(self, link):
        pass


Builder.load_string('''
<ChatClient>:
    BoxLayout:
        orientation: "vertical"
        size: root.size
        
        ScrollView:
            scroll_y:0
            BoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: self.minimum_height
                padding: [12, 0, 12, 0]
                spacing: 10
                id:main_view
        ShiftEnterTextInput:
            id:textbox
            size_hint_y: .1
''')

class ChatClient(Screen):
    
    #kivy string property indicating the network address of the chat
    chat_address = StringProperty()
    
    #called by Kivy when the screen is entered (displayed)
    def on_enter(self):
        #self.ids["textbox"].font_name=utf8_font_path
        self.ids["textbox"].focus = True
        self.ids["textbox"].text_validate_unfocus = False
        self.ids["textbox"].bind(on_text_validate=self.send_message)
        self.ids["textbox"].bind(on_key_pressed=self.key_pressed_event)
        
        #indicates if the user is typing or not
        self.isTyping = False
        
        #current typing status of all clients
        self.current_typing_msg = ""
        self.typing_widget = None
        
        self.network_interface = NetworkInterface(data_received_callback = self.receive_message, connection_made_callback = self.connection_made)
    
    def connection_made(self):
        #connection is established, connect to the target address
        message = NetworkMessage(self.chat_address, "ENTER", "")
        self.network_interface.send(message)
    
    def send_message(self, *args):
        msg = self.ids["textbox"].text
        
        if msg and self.network_interface:
            self.isTyping = False
            message = NetworkMessage(self.chat_address, "APPEND", msg)
            self.network_interface.send(message)
            self.ids["textbox"].text = ""
    
    def receive_message(self, message):
        if message.command == "IS_TYPING":
            self.add_typing_message(message.content)
            return
        
        #TODO: clean up code below
        if message.command == "INIT_CONTENT":
            for item in message.content:
                text_color_str = "000000"
                self.print_message(convert_utc_to_local(item[0]) + " " + item[1] + " : " + item[2], \
                                   text_color_str, item[1])
        elif message.command == "APPEND":
            item = message.content
            text_color_str = "000000"
            self.print_message(convert_utc_to_local(item[0]) + " " + item[1] + " : " + item[2], \
                               text_color_str, item[1])
        elif message.command == "NOTIFICATION_NEW_CLIENT":
            item = message.content
            #red for notifications
            text_color_str = "ff0000"
            self.print_message(convert_utc_to_local(item[0]) + " " + \
                               "  A new guest is here \^_^/ : " + item[1], \
                               text_color_str)
        elif message.command == "NOTIFICATION_CLIENT_LIST":
            #we receive a list [time, username, otheruser1, otheruser2, ...]
            #red for notifications
            text_color_str = "ff0000"
            text = convert_utc_to_local(message.content[0])
            if len(message.content) > 2:
                text += "  Currently connected guests: "
                for item in message.content[2:]:
                    text += item + " "
            else:
                text += "  No other guest currently connected."
            text += "\nYou are guest : " + message.content[1]
            self.print_message(text, text_color_str)
        elif message.command == "NOTIFICATION_CLIENT_LEFT":
            #red for notifications
            text_color_str = "ff0000"
            self.print_message(convert_utc_to_local(message.content[0]) + "  Chat left by " + \
                               message.content[1], text_color_str)
    
    def print_message(self, msg, text_color_str, username=None, isTyping = False):
        self.remove_typing_message()
        label = CustomLabel()
        label.text = "[color=" + text_color_str + "]" + format_links(msg) + "[/color]"
        if username == MainUser.username:
            #for message from the user itself, blue background and label on the right
            label.bcolor = [0.8,0.93,1,1]
            label.pos_hint = {'right': 1}
            
        self.ids["main_view"].add_widget(label)
        
        if isTyping:
            self.typing_widget = label
    
    #============= typing status ===========================
    #typing status is done by storing the current state of typing status
    #when the status changes, we remove the current status from the label, and display the new one (if any)
    def add_typing_message(self, msg):
        text_color_str = "0000ff"
        if self.current_typing_msg != "":
            self.current_typing_msg += "\n"
        self.current_typing_msg += msg + " is typing..."
        self.print_message(self.current_typing_msg, text_color_str, isTyping = True)
    
    def remove_typing_message(self):
        if not self.typing_widget is None:
            self.ids["main_view"].remove_widget(self.typing_widget)
            self.typing_widget = None
            self.current_typing_msg = ""
    
    #called when a key is pressed in the input
    def key_pressed_event(self, *args):
        #if the user was not already typing, send a TYPING message to the server
        if not self.isTyping:
            self.isTyping = True
            message = NetworkMessage(self.chat_address, "IS_TYPING", "")
            self.network_interface.send(message)
