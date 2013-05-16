import argparse

import gridfs
import pymongo


def parse_args():
    parser = argparse.ArgumentParser(
        description='Dump from "media" collection into GridFS')
    parser.add_argument(
        '--wipe', '-w', action='store_true', default=False,
        help="Wipe MongoDB before importing")

    args = parser.parse_args()
    return args


def main(args):
    db = pymongo.Connection(safe=True).motorblog

    if args.wipe:
        print 'Wiping'
        db.fs.files.remove()
        db.fs.chunks.remove()

    fs = gridfs.GridFS(db)

    print 'Migrating', db.media.count(), 'media from "media" to gridfs'
    print

    for media in db.media.find():
        _id = media['_id']
        print _id, media['type'], media['mod']

        try:
            gridout = fs.get_last_version(filename=_id)
            assert gridout.length == media['length']
            print 'Already done'
        except gridfs.NoFile:
            gridin = fs.new_file(filename=_id, content_type=media['type'])
            gridin.write(media['content'])
            gridin.close()
            print 'Done'


if __name__ == '__main__':
    main(parse_args())
