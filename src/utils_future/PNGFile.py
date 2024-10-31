import os
import tempfile
from functools import cached_property

import cv2
import numpy as np
from PIL import Image
from utils import File, Log

log = Log("PNGFile")


class PNGFile(File):
    @staticmethod
    def temp_png_path():
        return tempfile.mktemp(suffix=".png")

    def thicken(self, output_image_path, thickness=3) -> "PNGFile":

        image = cv2.imread(self.path, cv2.IMREAD_UNCHANGED)

        # Check the number of channels in the image
        if len(image.shape) == 2:  # Grayscale image
            gray = image
        elif len(image.shape) == 3 and image.shape[2] == 4:  # RGBA image
            gray = cv2.cvtColor(image, cv2.COLOR_BGRA2GRAY)
        else:  # RGB image
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # Threshold the image to get a binary image
        _, binary = cv2.threshold(gray, 128, 255, cv2.THRESH_BINARY_INV)

        # Create a kernel for dilation
        kernel = np.ones((thickness, thickness), np.uint8)

        # Dilate the image to thicken the edges
        dilated = cv2.dilate(binary, kernel, iterations=1)

        # Invert the image back
        thickened_edges = cv2.bitwise_not(dilated)

        # Save the thickened image
        cv2.imwrite(output_image_path, thickened_edges)
        log.info(f"[thicken] Wrote {output_image_path}")

        return PNGFile(output_image_path)

    @cached_property
    def bbox(self):
        im = Image.open(self.path).convert("RGBA")
        width, height = im.size
        min_x, min_y, max_x, max_y = width, height, 0, 0
        for x in range(width):
            for y in range(height):
                r, g, b, _ = im.getpixel((x, y))
                if r + g + b < 128:
                    min_x = min(min_x, x)
                    min_y = min(min_y, y)
                    max_x = max(max_x, x)
                    max_y = max(max_y, y)

        return min_x, min_y, max_x, max_y

    def crop(self, output_image_path, bbox) -> "PNGFile":
        min_x, min_y, max_x, max_y = bbox
        im = Image.open(self.path).convert("RGBA")
        im_cropped = im.crop((min_x, min_y, max_x, max_y))
        im_cropped.save(output_image_path)
        log.info(f"[crop] Wrote {output_image_path}.")
        return PNGFile(output_image_path)

    def center(
        self, output_image_path, background_color=(255, 255, 255, 0)
    ) -> "PNGFile":
        min_x, min_y, max_x, max_y = self.bbox
        cropped = self.crop(self.temp_png_path(), self.bbox)
        x_span = max_x - min_x
        y_span = max_y - min_y

        width = height = max(x_span, y_span)
        im = Image.open(cropped.path).convert("RGBA")
        im_centered = Image.new("RGBA", (width, height), background_color)
        x_offset = (width - x_span) // 2
        y_offset = (height - y_span) // 2
        im_centered.paste(im, (x_offset, y_offset))
        im_centered.save(output_image_path)
        log.info(f"[center] Wrote {output_image_path}.")
        return PNGFile(output_image_path)

    def resize(self, output_image_path, dim) -> "PNGFile":
        im = Image.open(self.path).convert("RGBA")
        im_resized = im.resize(dim)
        im_resized.save(output_image_path)
        log.info(f"[resize] Wrote {output_image_path}.")
        return PNGFile(output_image_path)

    def make_transparent(
        self, output_image_path, dim, foreground_color, background_color
    ) -> "PNGFile":

        im = Image.open(self.path).convert("RGBA")

        rf, gf, bf = foreground_color
        rb, gb, bb = background_color

        im_norm = Image.new("RGBA", im.size, (rb, gb, bb, 0))

        for x in range(dim):
            for y in range(dim):
                r, g, b, _ = im.getpixel((x, y))
                if r + g + b < 128:
                    im_norm.putpixel((x, y), (rf, gf, bf, 255))

        im_norm.save(output_image_path)
        log.info(f"[normalize] Wrote {output_image_path}.")
        return PNGFile(output_image_path)

    def normalize(
        self, output_image_path, dim, foreground_color, background_color
    ) -> "PNGFile":
        if os.path.exists(output_image_path):
            log.info(f"[normalize] {output_image_path} already exists.")
            return PNGFile(output_image_path)

        thickened = self.thicken(self.temp_png_path())
        cropped = thickened.crop(self.temp_png_path(), self.bbox)
        centered = cropped.center(self.temp_png_path(), background_color)
        resized = centered.resize(self.temp_png_path(), (dim, dim))
        transparent = resized.make_transparent(
            output_image_path, dim, foreground_color, background_color
        )

        log.info(f"[normalize] Wrote {output_image_path}.")
        return transparent
