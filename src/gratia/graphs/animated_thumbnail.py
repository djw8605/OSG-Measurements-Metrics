
import Image, ImageChops
import string, struct

from GifImagePlugin import getheader, getdata

# Part of this is from gifmaker, which is a script from PIL
class image_sequence:
    def __init__(self, im):
        self.im = im
    def __getitem__(self, ix):
        try:
            if ix:
                self.im.seek(ix)
            return self.im
        except EOFError:
            raise IndexError # end of sequence

def makedelta(fp, sequence):
    """Convert list of image frames to a GIF animation file"""

    frames = 0

    previous = None

    for im in sequence:

        #
        # FIXME: write graphics control block before each frame
        if not previous:

            # global header
            for s in getheader(im) + [get_loop(), get_image_control(500)] + getdata(im):
                fp.write(s)
        else:

            # delta frame
            delta = ImageChops.subtract_modulo(im, previous)

            bbox = delta.getbbox()

            if bbox:

                # compress difference
                for s in [get_image_control(500)] + getdata(im.crop(bbox), offset = bbox[:2]):
                    fp.write(s)

            else:
                # FIXME: what should we do in this case?
                raise Exception("Undefined bbox.")

        previous = im.copy()

        frames = frames + 1

    fp.write(";")

    return frames

def get_loop():
    return struct.pack('BBB11sBBHB', 33, 255, 11, "NETSCAPE2.0", 3, 1, 0, 0)

def get_image_control(delay):
    #return ''
    return struct.pack('BBBBHBB', 0x21, 0xF9, 4, 0, delay, 0, 0)

#end of gifmaker stuff.  See original copyright notice

def animated_gif(outfile, infiles, height, greyscale=True):
    ims = []
    for infile in infiles:
        im = Image.open(infile)
        im.load()
        im.thumbnail(height, Image.ANTIALIAS)
        #print im.size
        if (greyscale and im.mode != 'L'):
            im = im.convert('L')
        if (not greyscale and im.mode != 'P'):
            im = im.convert('P')
        ims.append(im)
    fp = open(outfile, "wb")
    makedelta(fp, ims)
    fp.close()

