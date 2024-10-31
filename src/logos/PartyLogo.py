import os
import time
from functools import cached_property

import requests
from bs4 import BeautifulSoup
from PIL import Image
from utils import Log

from logos.PARTY_TO_SYMBOL import PARTY_TO_SYMBOL

log = Log("PartyLogo")


class PartyLogo:
    DIR_ORIGINAL_IMAGES = os.path.join("images", "original")

    DIM = 512

    def __init__(self, symbol):
        self.symbol = symbol

    @cached_property
    def original_image_path(self):
        return os.path.join(
            PartyLogo.DIR_ORIGINAL_IMAGES, f"{self.symbol}.png"
        )

    def generate_black_image(self):
        return self.generate_norm_image("black", (0, 0, 0), (255, 255, 255))

    def generate_white_image(self):
        return self.generate_norm_image(
            "white", (255, 255, 255), (255, 255, 255)
        )

    def generate_norm_image(
        self, norm_type, foreground_color, background_color
    ):
        dir_norm_images = os.path.join("images", norm_type)
        if not os.path.exists(dir_norm_images):
            os.makedirs(dir_norm_images)

        image_path = os.path.join(dir_norm_images, f"{self.symbol}.png")
        if os.path.exists(image_path):
            log.warning(f"Already generated {image_path}.")
            return

        im = Image.open(self.original_image_path)
        im_resized = im.resize((PartyLogo.DIM, PartyLogo.DIM)).convert("RGBA")

        rf, gf, bf = foreground_color
        rb, gb, bb = background_color

        im_norm = Image.new("RGBA", im_resized.size, (rb, gb, bb, 0))

        for x in range(PartyLogo.DIM):
            for y in range(PartyLogo.DIM):
                r, g, b, _ = im_resized.getpixel((x, y))
                if r + g + b < 128:
                    im_norm.putpixel((x, y), (rf, gf, bf, 255))

        im_norm.save(image_path)
        log.info(f"Generated {image_path}.")

    @staticmethod
    def get_symbol(file_name):
        return file_name.split(".")[0]

    @staticmethod
    def list_all():
        party_logo_list = []
        for file_name in os.listdir(PartyLogo.DIR_ORIGINAL_IMAGES):
            if not file_name.endswith(".png"):
                continue
            symbol = PartyLogo.get_symbol(file_name)
            party_logo_list.append(PartyLogo(symbol))
        log.info(f"Found {len(party_logo_list)} party logos.")
        return party_logo_list

    @staticmethod
    def download_all():
        if not os.path.exists(PartyLogo.DIR_ORIGINAL_IMAGES):
            os.makedirs(PartyLogo.DIR_ORIGINAL_IMAGES)
        PartyLogo.download_from_remote_dir(
            "https://results.elections.gov.lk" + "/assets/images/symbols/"
        )
        PartyLogo.download_from_remote_dir(
            "https://results.elections.gov.lk"
            + "/assets/images/symbols/New%20folder/"
        )

    @staticmethod
    def download_from_remote_dir(remote_dir):
        log.info(f"Downloading images from {remote_dir}.")
        response = requests.get(remote_dir)
        html = response.content

        soup = BeautifulSoup(html, "html.parser")
        link_list = soup.find_all("a")

        for link in link_list:
            image_base_name = link["href"]
            if not image_base_name.endswith(".png"):
                return None
            PartyLogo.download_remote_image(remote_dir, image_base_name)

    @staticmethod
    def download_remote_image(remote_dir, image_base_name):

        party_id = image_base_name.split(".")[0]
        if party_id not in PARTY_TO_SYMBOL:
            log.warning(f"Skipping {party_id}.")
        symbol = PARTY_TO_SYMBOL[party_id].replace(" ", "_")
        image_path = os.path.join(
            PartyLogo.DIR_ORIGINAL_IMAGES, f"{symbol}.png"
        )
        if os.path.exists(image_path):
            log.warning(f"Already downloaded {image_path}.")
            return None

        timeout = 1
        while True:
            try:
                img_data = requests.get(
                    remote_dir + image_base_name, timeout=timeout
                ).content
                break
            except requests.exceptions.RequestException:
                log.error(
                    f"Error downloading {image_base_name}. "
                    + f"Retrying in {timeout} seconds."
                )
                time.sleep(timeout)
                timeout *= 2

        with open(image_path, "wb") as fout:
            fout.write(img_data)

        log.info(f"Downloaded {image_path}.")


if __name__ == "__main__":
    PartyLogo.download_all()
    for party_logo in PartyLogo.list_all():
        party_logo.generate_black_image()
        party_logo.generate_white_image()
