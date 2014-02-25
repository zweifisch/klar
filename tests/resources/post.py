from klar import method

def show(post_id):
    return 'post: %s' % post_id

@method('patch')
def upvote(post_id):
    return 'upvote: %s' % post_id
