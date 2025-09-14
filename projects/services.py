from .models import * 
from .utils import *

def save_comment(task,author, content):
    comment = TaskComment.objects.create(task = task, author = author, content = content)

    full_name= extract_mentions(content)
    mentioned_users = User.objects.filter(username_in =full_name)
    comment.mentions.set(mentioned_users)
    