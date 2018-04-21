import argparse
import numpy as np
import os
from glob import glob
import lsh
from timeit import default_timer as timer
import sys
import pickle
import shutil


def video_id_from_name(name):
    return os.path.splitext(os.path.basename(name))[0]


def parse_database(database_path):
    return [(np.load(f).flatten(), video_id_from_name(f)) for f in glob(os.path.join(database_path, '*.npy'))]


def top_k_naive(database, probe, k):
    database.sort(key=lambda v: np.linalg.norm(v[0] - probe))
    return database[0:k]


def lsh_database(database, basis):
    return [(lsh.lsh(r, basis), v) for r, v in database]


def top_k_lsh(database, probe, k):
    database.sort(key=lambda v: lsh.hamming_distance(v[0], probe))
    return database[0:k]


def human_size(bytes, units=[' bytes','KB','MB','GB','TB', 'PB', 'EB']):
    """ Returns a human readable string reprentation of bytes"""
    return str(bytes) + units[0] if bytes < 1024 else human_size(bytes >> 10, units[1:])


def copy_video(name, search_root, dst):
    matches = glob('{}/**/{}'.format(search_root, name), recursive=True)
    shutil.copy(matches[0], dst)


def main(args):
    database = parse_database(args.database)
    probe = np.load(args.probe)

    os.makedirs(args.output, exist_ok=True)
    copy_video(video_id_from_name(args.probe), args.videos, os.path.join(args.output, 'probe.avi'))

    start = timer()
    k_naive = top_k_naive(database, probe, args.k)
    end = timer()

    os.makedirs(os.path.join(args.output, 'naive'), exist_ok=True)
    with open(os.path.join(args.output, 'naive', 'results.txt'), 'w') as f:
        for i in range(len(k_naive)):
            v = k_naive[i]
            d = np.linalg.norm(v[0] - probe)
            f.write('Video ID: {}, Distance: {}\n'.format(v[1], d))

            copy_video(v[1], args.videos, os.path.join(args.output, 'naive', '{}.avi'.format(i)))

        f.write('Time: {} s\n'.format(end - start))
        f.write('DB Memory: {}\n'.format(human_size(sys.getsizeof(pickle.dumps(database)))))

    for basis_size in args.lsh:
        basis = lsh.generate_basis(basis_size, database[0][0].shape[0])
        probe_lsh = lsh.lsh(probe, basis)
        database_lsh = lsh_database(database, basis)

        start = timer()
        k_l = top_k_lsh(database_lsh, probe_lsh, args.k)
        end = timer()

        result_dir = 'lsh_{}'.format(basis_size)
        os.makedirs(os.path.join(args.output, result_dir), exist_ok=True)

        with open(os.path.join(args.output, result_dir, 'results.txt'), 'w') as f:
            for i in range(len(k_l)):
                v = k_l[i]
                d = lsh.hamming_distance(v[0], probe_lsh)
                f.write('Video ID: {}, Distance: {}\n'.format(v[1], d))

                copy_video(v[1], args.videos, os.path.join(args.output, result_dir, '{}.avi'.format(i)))

            f.write('Time: {} s\n'.format(end - start))
            f.write('DB Memory: {}\n'.format(human_size(sys.getsizeof(pickle.dumps(database_lsh)))))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--lsh', action='append', type=int, help='Get results for this LSH basis size')
    parser.add_argument('--database', help='Path to the database representations')
    parser.add_argument('--probe', help='Path to the probe representation')
    parser.add_argument('--k', type=int, default=3, help='Retrieve top k videos')
    parser.add_argument('--output', help='Path to output package location')
    parser.add_argument('--videos', help='Path to UCF101 original videos')
    args = parser.parse_args()
    main(args)
