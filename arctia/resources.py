import os
import pygame
from pkg_resources import resource_stream, resource_filename

def get_resource_filename(path):
    """
    Return the filename of a resource.

    :param path: the path to the resource
    :returns: the real filename of the resource
    """
    return resource_filename('arctia', path)

def get_resource_stream(path):
    """
    Return a stream to the contents of a named resource.
    
    :param path: the path to the resource
    :returns: a file-like stream to the resource
    """
    return resource_stream('arctia', path)
    
def load_image(path):
    """
    Load an image resource and return it as a surface.

    :param path: the path to the image
    :returns: the image as a pygame surface
    """
    with get_resource_stream(path) as f:
        return pygame.image.load(f, path)
    
def load_music(path):
    """
    Load a music resource and prepare it for playing.

    :param path: the path to the sound
    """
    return pygame.mixer.music.load(get_resource_filename(path))
