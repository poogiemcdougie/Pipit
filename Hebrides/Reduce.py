from pathlib import Path

"""Resize JPEG images with Lanczos and save tagged copies."""

import argparse
from pathlib import Path

from PIL import Image, ImageOps

# Name and path resolved.
def fullname(o): return str(o.resolve())

# File size in KB int.
def fsize(f: Path): return f.stat().st_size // 1024

# Return tagged name, e.g. foo.jpg -> foo_web.jpg. If verify=true, return
# true if path already has tag.
def tag_file(source: Path, tag, verify = False):
    if verify:
        return source.stem.endswith(tag)
    return source.stem + tag + source.suffix

def resize_jpeg(sce: Path, dst: Path, max_size, quality) -> bool:
    """
        Write a resized JPEG. 
        Return True on success.
    """

    sce = sce.resolve()

    '''
        quality=95: very high quality, larger file.
        quality=90: high quality, usually an excellent choice for website photographs.
        quality=75: reasonable quality, smaller file.
        quality=50: more visible compression artefacts.
    '''
    try:
        with Image.open(sce) as image:
            # Apply EXIF orientation before calculating the output dimensions.
            image = ImageOps.exif_transpose(image)
            image.thumbnail((max_size, max_size), Image.Resampling.LANCZOS)

            # JPEG cannot store alpha; composite transparency onto white if needed.
            if image.mode in ("RGBA", "LA") or (
                image.mode == "P" and "transparency" in image.info
            ):
                rgba = image.convert("RGBA")
                background = Image.new("RGB", rgba.size, "white")
                background.paste(rgba, mask=rgba.getchannel("A"))
                image = background
            elif image.mode != "RGB":
                image = image.convert("RGB")

            image.save(dst, "JPEG", quality=quality, optimize=True)

        print(f"{fullname(sce)} {fsize(sce):,} KB\n    {fullname(dst)}  {fsize(dst):,} KB")
        return True
    except Exception as exc:
        print(f"ERROR {sce}: {exc}")
        return False


def main() -> int:

    def_tag = "_web"

    parser = argparse.ArgumentParser(
        description="Resize JPEGs with Lanczos and save name_TAG.jpg copies.",
        # This one shows defaults at end of help text.
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "-dry", action="store_true",
        help="dry-run - list files and targets and exit",
    )
    parser.add_argument(
        "-quality", default=90,
        help="compression quality: 75=reasonable, 95=very high",
    )
    parser.add_argument(
        "-tag", default=def_tag,
        help="name.jpg becomes name+tag.jpg",
    )
    parser.add_argument(
        "-dir",
        help="directory to scan, or base directory for a filename without a path",
    )
    parser.add_argument(
        "-dest_dir",
        help="directory to write files into, default same as source",
    )
    parser.add_argument(
        "-file",
        help="process only this file; relative paths without a directory use -dir",
    )
    parser.add_argument(
        "-outfile",
        help="write to this file with -file, no tag used",
    )
    parser.add_argument(
        "-size", type=int, default=2000,
        help="maximum width and height in pixels",
    )
    args = parser.parse_args()


    if args.size < 1:
        parser.error("-size must be a positive integer")

    tag = args.tag

    base_dir = Path("." if args.dir is None else args.dir).expanduser()
    if not base_dir.is_dir():
        print(f"ERROR Directory not found: {base_dir}")
        return 1

    '''
        -file 
            foo.jpg
            Images/foo.jpg
            ~/Images/foo.jpg
            /Images/foo.jpg
            [resolve() follows symlinks and returns absolute path.]
        If -file try is_file() -> fails -> exit.
            Extract absolute path to base_dir using resolve()
        If -outfile then -dst_dir disallowed, either use same dir
        as source, or include dir in -outfile as is usual approach.
    '''

    files = []
    use_tag = True

    # If -file, no -dir, include dir in -file if needed.
    # If -file and no -outfile, use the tag to create from -file.
    # If -outfile, this is the complete name, no tag applies.
    if args.file:
        if args.dir is not None:
            parser.error("Include path in -file, not -dir (for multiple files)")
        f = Path(args.file).expanduser()
        if not f.is_file():
            parser.error(f"No file: {fullname(args.file)}")
        base_dir = f.resolve().parent # Abs path, follow symlinks as well.
        files = [f]
        if args.outfile:
            if args.dst_dir is not None:
                parser.error("Include path in -outfile, not -dst_dir")
            if args.tag != def_tag:
                parser.error("-outfile is complete name, not tagged")
            files = [(f, args.outfile)]
            use_tag = False

    # Generate the tagged names for output files. This is all except for -out_file
    # which is not tagged.
    if use_tag:    
        v = args.dest_dir
        dst_dir = Path(base_dir if v is None else v).expanduser()

        if not files:
            files = sorted(
                p for p in base_dir.iterdir()
                if p.is_file() and p.suffix.lower() in {".jpg", ".jpeg"} and 
                    not tag_file(p, tag, True)
                )

        files = [(p, Path(dst_dir) / tag_file(p, tag)) for p in files]

        if not files:
            print("No files found.")
            return 0


    if args.dry:
        print(*[f"{fullname(sce)} \n    -> {fullname(dst)}" for (sce, dst) in files], sep="\n")
        return 0

    
    successes = sum(resize_jpeg(sce, dst, args.size, args.quality) for (sce, dst) in files)

    print(f"Finished: {successes}/{len(files)} file(s) processed.")
    
    return 0 if successes == len(files) else 1


if __name__ == "__main__":
    raise SystemExit(main())






