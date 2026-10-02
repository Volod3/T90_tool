#!/usr/bin/env python3

# /// script
# requires-python = ">=3.9"
# dependencies = ["hidapi>=0.14", "pillow>=10"]
# ///

import argparse
import struct
import sys
import time
from pathlib import Path

import hid
from PIL import Image


VID = 0x19F5
PID = 0x3245

DEST = 0xAF
REPLY = 0xDF

FN_GET_INFO = 0x10
FN_SET_FW_INFO = 0x11
FN_START = 0x12
FN_DATA = 0x13
FN_END = 0x14
FN_SET_BOOT = 0x15

FILE_LOGO = 0xA1

CHUNK_SIZE = 32

LOGO_WIDTH = 160
LOGO_HEIGHT = 40
LOGO_SIZE = LOGO_WIDTH * LOGO_HEIGHT * 2

MAX_LOGO_PAYLOAD = 0x3800


def checksum(data: bytes) -> int:
    return (-sum(data)) & 0xFF


def make_frame(fn: int, seq: int = 0, data: bytes = b"") -> bytes:
    if len(data) > 255:
        raise ValueError("Дані для одного HID-фрейму завеликі")

    frame = bytes([
        DEST,
        fn,
        seq & 0xFF,
        len(data),
    ]) + data

    return frame + bytes([checksum(frame)])


def hid_write(dev, frame: bytes):
    packet = b"\x00" + frame

    if len(packet) > 65:
        raise ValueError("HID packet > 65 bytes")

    packet = packet.ljust(65, b"\x00")
    dev.write(packet)


def hid_command(
    dev,
    fn: int,
    seq: int = 0,
    data: bytes = b"",
    timeout: int = 1000,
    retries: int = 1,
):
    frame = make_frame(fn, seq, data)

    last_error = None

    for attempt in range(retries):
        try:
            hid_write(dev, frame)

            response = bytes(dev.read(64, timeout))

            if not response:
                raise RuntimeError("T90 не відповів")

            if response[0] != REPLY:
                raise RuntimeError(
                    "Невірна відповідь T90: "
                    + response[:20].hex(" ")
                )

            if len(response) < 5:
                raise RuntimeError("Занадто коротка відповідь")

            r_fn = response[1]
            r_seq = response[2]
            length = response[3]

            if r_fn != fn:
                raise RuntimeError(
                    f"Невірна команда у відповіді: "
                    f"очікувалось 0x{fn:02X}, отримано 0x{r_fn:02X}"
                )

            end = 4 + length

            if end >= len(response):
                raise RuntimeError("Некоректна довжина відповіді")

            body = response[:end]
            received_checksum = response[end]

            if checksum(body) != received_checksum:
                raise RuntimeError(
                    "Помилка checksum: "
                    + response[:end + 1].hex(" ")
                )

            payload = response[4:end]

            return payload

        except Exception as e:
            last_error = e

            if attempt + 1 < retries:
                time.sleep(0.05)

    raise last_error


def open_t90():
    dev = hid.device()

    try:
        dev.open(VID, PID)
    except Exception as e:
        print()
        print("Не вдалося відкрити T90.")
        print("Помилка:", e)
        print()
        print("Перевір:")
        print("1. T90 вимкнений.")
        print("2. Затиснута кнопка B.")
        print("3. Підключений USB-C.")
        print("4. На екрані T90 написано Upgrade...")
        print()
        raise SystemExit(1)

    return dev


def get_info(dev):
    data = hid_command(
        dev,
        FN_GET_INFO,
        retries=3,
    )

    if len(data) != 21:
        raise RuntimeError(
            f"GET_INFO повернув {len(data)} байт замість 21"
        )

    dev_type = struct.unpack_from("<H", data, 0)[0]
    hw_ver = data[2]
    app_ver = data[3]
    fw_num = data[4]
    run_flag = data[5]
    serial = data[6:18]
    year = data[18]
    month = data[19]
    day = data[20]

    return {
        "dev_type": dev_type,
        "hw_ver": hw_ver,
        "app_ver": app_ver,
        "fw_num": fw_num,
        "run_flag": run_flag,
        "serial": serial.hex(),
        "year": year,
        "month": month,
        "day": day,
    }


def print_info(info):
    print()
    print("=== T90 INFO ===")
    print(f"Device type : 0x{info['dev_type']:04X}")
    print(f"HW version  : 0x{info['hw_ver']:02X}")
    print(f"APP version : 0x{info['app_ver']:02X}")
    print(f"FW number   : 0x{info['fw_num']:02X}")
    print(f"Run flag    : 0x{info['run_flag']:02X}")
    print(f"Serial      : {info['serial']}")
    print(
        f"Date        : "
        f"{info['year']:02X}-"
        f"{info['month']:02X}-"
        f"{info['day']:02X}"
    )
    print()


def require_t90(info):
    if info["dev_type"] != 0x0208:
        raise RuntimeError(
            f"Несподіваний device type: 0x{info['dev_type']:04X}"
        )

    if info["run_flag"] != 0xB0:
        raise RuntimeError(
            f"T90 не в режимі Upgrade. "
            f"run_flag=0x{info['run_flag']:02X}"
        )


def image_to_rgb565(image_path: Path) -> bytes:
    print(f"Відкриваю: {image_path}")

    image = Image.open(image_path)

    print(
        f"Оригінальний розмір: "
        f"{image.width}×{image.height}"
    )

    image = image.convert("RGB")

    # Саме РОЗТЯГУЄМО до 160×40,
    # як ти вже зробив зі своєю картинкою.
    image = image.resize(
        (LOGO_WIDTH, LOGO_HEIGHT),
        Image.Resampling.LANCZOS,
    )

    pixels = image.load()

    output = bytearray()

    for y in range(LOGO_HEIGHT):
        for x in range(LOGO_WIDTH):
            r, g, b = pixels[x, y]

            # Формат T90 RGB565:
            # byte 0 = G[4:2] + B[7:3]
            # byte 1 = R[7:3] + G[7:5]

            first = ((g & 0x1C) << 3) | (b >> 3)
            second = (r & 0xF8) | (g >> 5)

            output.append(first)
            output.append(second)

    return bytes(output)


def make_logo_payload(image_path: Path) -> bytes:
    pixels = image_to_rgb565(image_path)

    if len(pixels) != LOGO_SIZE:
        raise RuntimeError(
            f"Неправильний розмір RGB565: {len(pixels)}"
        )

    payload = (
        b"ATKLOGO\x00"
        + struct.pack("<HH", LOGO_WIDTH, LOGO_HEIGHT)
        + pixels
    )

    if len(payload) != 12812:
        raise RuntimeError(
            f"Неправильний розмір logo payload: {len(payload)}"
        )

    if len(payload) > MAX_LOGO_PAYLOAD:
        raise RuntimeError("Логотип завеликий")

    return payload


def make_atk(payload: bytes, file_type: int) -> bytes:
    if file_type != FILE_LOGO:
        raise RuntimeError(
            "Цей скрипт дозволяє створювати тільки logo A1"
        )

    now = time.localtime()

    year = now.tm_year - 2000

    header = struct.pack(
        "<HBBBBIBBB",
        0x0208,          # device type
        10,              # HW version
        1,               # APP version
        file_type,       # A1 = logo
        CHUNK_SIZE,      # chunk size
        len(payload),
        year,
        now.tm_mon,
        now.tm_mday,
    )

    # T90 очікує payload XOR FF
    encrypted_payload = bytes(
        b ^ 0xFF for b in payload
    )

    return header + encrypted_payload


def print_logo_info(image_path, payload, atk):
    print()
    print("=== LOGO ===")
    print(f"Image       : {image_path}")
    print(f"Resolution  : {LOGO_WIDTH}×{LOGO_HEIGHT}")
    print(f"RGB565 data : {LOGO_SIZE} bytes")
    print(f"Payload     : {len(payload)} bytes")
    print(f"ATK size    : {len(atk)} bytes")
    print("fileType    : 0xA1 LOGO")
    print("Target      : 0x08006000")
    print()
    print("Перші байти payload:")
    print(payload[:32].hex(" "))
    print()
    print("Перші байти .atk:")
    print(atk[:32].hex(" "))
    print()


def send_result_check(dev, fn, data=b"", seq=0):
    response = hid_command(
        dev,
        fn,
        seq=seq,
        data=data,
        retries=3,
    )

    if not response:
        raise RuntimeError(
            f"T90 не повернув result для 0x{fn:02X}"
        )

    if response[0] != 0x00:
        raise RuntimeError(
            f"T90 повернув помилку для 0x{fn:02X}: "
            f"0x{response[0]:02X}"
        )

    return response


def flash_logo(dev, atk_data, dry_run=False):
    header = atk_data[:13]
    payload = atk_data[13:]

    print("Відправляю SET_FW_INFO...")

    send_result_check(
        dev,
        FN_SET_FW_INFO,
        header,
    )

    print("SET_FW_INFO: OK")

    if dry_run:
        print()
        print("DRY-RUN завершено.")
        print("START НЕ відправлявся.")
        print("Пам'ять T90 НЕ стиралася і НЕ змінювалася.")
        return

    print()
    print("START: очищення області логотипа...")
    send_result_check(dev, FN_START)
    print("START: OK")

    total = len(payload)
    sent = 0
    seq = 0

    print()
    print("Передача логотипа...")

    while sent < total:
        chunk = payload[sent:sent + CHUNK_SIZE]

        send_result_check(
            dev,
            FN_DATA,
            seq=seq,
            data=chunk,
        )

        sent += len(chunk)

        print(
            f"\r{sent:5d} / {total} bytes "
            f"({sent * 100 // total:3d}%)",
            end="",
            flush=True,
        )

        seq = (seq + 1) & 0xFF

    print()
    print("DATA: OK")

    print("END...")
    send_result_check(dev, FN_END)
    print("END: OK")

    print("COMMIT / SET_BOOT...")

    try:
        hid_command(
            dev,
            FN_SET_BOOT,
            timeout=1000,
            retries=1,
        )
    except Exception:
        # Після SET_BOOT T90 може одразу перезавантажитися,
        # тому відсутність відповіді тут допустима.
        pass

    print()
    print("Готово.")
    print("Від'єднай USB-C і увімкни T90 без утримання B.")


def command_probe():
    dev = open_t90()

    try:
        info = get_info(dev)
        print_info(info)

        require_t90(info)

        print("PROTOCOL CONFIRMED")
        print("T90 знаходиться в Upgrade mode.")
    finally:
        dev.close()


def command_logo(image_path: Path, dry_run: bool, yes: bool):
    if not image_path.exists():
        raise RuntimeError(
            f"Файл не знайдено: {image_path}"
        )

    payload = make_logo_payload(image_path)
    atk = make_atk(payload, FILE_LOGO)

    print_logo_info(image_path, payload, atk)

    # Спочатку підключаємось і тільки читаємо INFO.
    dev = open_t90()

    try:
        info = get_info(dev)
        print_info(info)
        require_t90(info)

        print("T90 перевірений: OK")

        if dry_run:
            print()
            print("=== DRY-RUN ===")
            flash_logo(
                dev,
                atk,
                dry_run=True,
            )
            return

        if not yes:
            print()
            print("УВАГА!")
            print("Зараз буде стерта ТІЛЬКИ область логотипа")
            print("і записаний новий логотип.")
            print()
            print("Bootloader 0xB0 НЕ використовується.")
            print("Firmware 0xA0 НЕ використовується.")
            print("Зараз використовується тільки LOGO 0xA1.")
            print()
            answer = input(
                "Якщо хочеш продовжити, напиши YES: "
            )

            if answer != "YES":
                print("Скасовано. T90 не змінювався.")
                return

        flash_logo(
            dev,
            atk,
            dry_run=False,
        )

    finally:
        dev.close()


def main():
    parser = argparse.ArgumentParser(
        description="Безпечний Linux CLI для логотипа Alientek T90"
    )

    sub = parser.add_subparsers(
        dest="command"
    )

    sub.add_parser(
        "probe",
        help="Перевірити T90 без запису",
    )

    logo = sub.add_parser(
        "logo",
        help="Записати логотип",
    )

    logo.add_argument(
        "image",
        type=Path,
        help="PNG/JPG зображення",
    )

    logo.add_argument(
        "--dry-run",
        action="store_true",
        help="Тільки перевірка, без стирання/запису",
    )

    logo.add_argument(
        "--yes",
        action="store_true",
        help="Не питати підтвердження",
    )

    args = parser.parse_args()

    if args.command == "probe":
        command_probe()
        return

    if args.command == "logo":
        command_logo(
            args.image,
            args.dry_run,
            args.yes,
        )
        return

    parser.print_help()


if __name__ == "__main__":
    main()
