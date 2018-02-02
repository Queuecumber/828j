import sys
sys.path.append('../')
import os
import file_constants as file_const
import data_sampling.data_args as data_args
import constants as const
import numpy as np
import cv2
import utils
import traceback

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

class TupleLoader:
    def __init__(self, args):
        self._tuples_path = utils.dataset_tuples(utils.get_dataset_path(file_const.dataset_name))

        train_tuple_path = os.path.join(self._tuples_path, 'train')
        val_tuple_path = os.path.join(self._tuples_path, 'val')
        self.train_lbls_ary = utils.pkl_read(os.path.join(train_tuple_path,'lbl.pkl'))
        self._num_training = self.train_lbls_ary.shape[0]
        self.val_lbls_ary = utils.pkl_read(os.path.join(val_tuple_path, 'lbl.pkl'))
        self._num_val = self.val_lbls_ary.shape[0]
        print('Num Training ',self._num_training, ' Num Validation',self._num_val)

        self._gen_nearby_frame = args[data_args.gen_nearby_frame]
        self._data_augmentation_enabled = args[data_args.data_augmentation_enabled]
        print('Near By ',self._gen_nearby_frame)

    def img_at_index(self,index,subset):
        im = None;
        while im is None:
            im = cv2.imread(self._tuples_path + '/'+subset+'/frame' + '%07d' % (index) + '.jpg')
            if(im is None):
                #print('File Missing ::',file_const.data_path + '/'+subset+'/frame' + '%07d' % (index) + '.jpg')
                index = index - 200;
        if(im.shape[0] < const.frame_height):
            im = cv2.copyMakeBorder(im, 1, 2, 1, 2, cv2.BORDER_REPLICATE)
        return im;


    def pkl_at_index(self,index,subset,ordered=True):
        pkl = None
        while pkl is None:
            pkl = utils.pkl_read(self._tuples_path + '/' + subset + '/frame' + '%07d' % (index) + '.pkl')
            if(pkl is None):
                index = index - 200;

        if(not ordered):

            # Swap 2 random frames only
            swap_channels = np.random.choice(pkl.shape[2],2,replace=False);

            # tmp_range = np.arange(pkl.shape[2])
            # x = tmp_range[swap_channels[0]]
            # tmp_range[swap_channels[0]] =  tmp_range[swap_channels[1]]
            # tmp_range[swap_channels[1]] = x
            # print('Correct Range = ',tmp_range)

            tmp  = pkl[:,:,swap_channels[0]].copy();
            pkl[:, :, swap_channels[0]] = pkl[:, :, swap_channels[1]]
            pkl[:, :, swap_channels[1]] = tmp;
            #save_pkls('ttuple', pkl[np.newaxis, :], 1, 'pkl')
        if (pkl.shape[0] < const.frame_height):
            npad = ((1, 2), (1, 2), (0, 0))
            pkl = np.lib.pad(pkl, npad , 'constant', constant_values=0)
        return pkl

    def unsupervised_next(self,subset, fix_label=None):
        subset_name = ''
        subset_size = 0
        if (subset == const.Subset.TRAIN):
            subset_name = 'train'
            subset_size = self._num_training
            ratio = 3
        elif (subset == const.Subset.VAL):
            subset_name = 'val'
            subset_size = self._num_val
            ratio = 2;
        elif (subset == const.Subset.TEST):
            img_set = self._test_activities

        pos_tuple = np.random.randint(low=0, high=subset_size, size=(const.batch_size));
        neg_tuple = np.random.randint(low=0, high=subset_size, size=(const.batch_size));

        words = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.frame_channels))
        contexts = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.context_channels))
        if self._gen_nearby_frame:
            nearby = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.frame_channels))

        labels = np.zeros((const.batch_size), dtype=np.int32)
        postive_ratio = 1 / ratio;
        if (fix_label == None):
            sampling_ratio = np.random.rand(const.batch_size);
        elif (fix_label == 1):
            sampling_ratio = np.zeros(const.batch_size);
        elif (fix_label == -1):
            #sampling_ratio = np.ones(const.batch_size);
            sampling_ratio = np.random.rand(const.batch_size) * (1-postive_ratio)+ postive_ratio ;
        neg_count = 0
        pos_count = 0
        order_neg_count = 0
        for batch_idx in np.arange(0, const.batch_size):
            # print(pos_tuple[batch_idx])

            if (sampling_ratio[batch_idx] < postive_ratio ):
                pos_count += 1
                labels[batch_idx] = 1;
                try:
                    words[batch_idx, :, :] = self.img_at_index(pos_tuple[batch_idx], subset_name)
                    contexts[batch_idx, :, :] = self.pkl_at_index(pos_tuple[batch_idx], subset_name)
                except:
                    traceback.print_exc()
                    print('Something was wrong when reading pos tuple at index', pos_tuple[batch_idx])
                    words[batch_idx, :, :] = self.img_at_index(0, subset_name)
                    contexts[batch_idx, :, :] = self.pkl_at_index(0, subset_name)
            else:

                labels[batch_idx] = -1;
                try:
                    words[batch_idx, :, :] = self.img_at_index(pos_tuple[batch_idx], subset_name)
                    if ((sampling_ratio[batch_idx] -postive_ratio)/(1-postive_ratio) <= 0.75 ):
                        contexts[batch_idx, :, :] = self.pkl_at_index(pos_tuple[batch_idx], subset_name,ordered=False)
                        order_neg_count += 1
                    else:
                        contexts[batch_idx, :, :] = self.pkl_at_index(neg_tuple[batch_idx], subset_name)
                        neg_count += 1
                except:
                    traceback.print_exc()
                    print('Something was wrong when reading neg tuple at index', pos_tuple[batch_idx],neg_tuple[batch_idx])
                    words[batch_idx, :, :] = self.img_at_index(1, subset_name)
                    contexts[batch_idx, :, :] = self.pkl_at_index(0, subset_name)

        #print(pos_count,neg_count,order_neg_count)
        # return words, contexts, labels

        labels[labels == -1] = 0
        labels_hot_vector = np.zeros((const.batch_size, 2))
        labels_hot_vector[np.arange(const.batch_size), labels] = 1

        if self._gen_nearby_frame:
            return words, nearby, contexts, labels_hot_vector
        else:
            return words, contexts, labels_hot_vector

    def supervised_next(self, subset, fix_label=None):
        subset_name = ''
        subset_size = 0
        if (subset == const.Subset.TRAIN):
            subset_name = 'train'
            subset_size = self._num_training
            class_lbls = self.train_lbls_ary
        elif (subset == const.Subset.VAL):
            subset_name = 'val'
            subset_size = self._num_val
            class_lbls = self.val_lbls_ary
        elif (subset == const.Subset.TEST):
            img_set = self._test_activities

        if (fix_label == None):
            tuple = np.random.randint(low=0, high=subset_size, size=(const.batch_size));
        else:
            samples_pool = np.where(class_lbls == fix_label)[0]
            #print(samples_pool)
            tuple = np.random.choice(samples_pool,const.batch_size)
            #tuple = np.random.randint(low=0, high=subset_size, size=(const.batch_size));

        words = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.frame_channels))
        contexts = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.context_channels))
        if self._gen_nearby_frame:
            nearby = np.zeros((const.batch_size, const.frame_height, const.frame_width, const.frame_channels))

        labels = np.zeros((const.batch_size), dtype=np.int32)


        for batch_idx in np.arange(0, const.batch_size):

            try:
                found = False
                while not found:
                    if (os.path.exists(file_const.data_path + '/'+subset_name+'/frame' + '%07d' % (tuple[batch_idx]) + '.jpg')):
                        labels[batch_idx] = class_lbls[tuple[batch_idx]];
                        words[batch_idx, :, :] = self.img_at_index(tuple[batch_idx], subset_name)
                        contexts[batch_idx, :, :] = self.pkl_at_index(tuple[batch_idx], subset_name)
                        found = True;
                    else:
                        tuple[batch_idx] = tuple[batch_idx] - 200
            except:
                traceback.print_exc()
                print('Something was wrong when reading tuple at index',tuple[batch_idx])
                labels[batch_idx] = class_lbls[0];
                words[batch_idx, :, :] = self.img_at_index(0, subset_name)
                contexts[batch_idx, :, :] = self.pkl_at_index(0, subset_name)


        labels_hot_vector = np.zeros((const.batch_size, file_const.num_classes))
        labels_hot_vector[np.arange(const.batch_size), labels] = 1
        if self._gen_nearby_frame:
            return words, nearby, contexts, labels_hot_vector
        else:
            return words, contexts, labels_hot_vector

    ## subset : indicate whether to use Train or Val
    ## fix_label : typically using with validation set, to force all tuple belong to certain class.
    ## For example, you want a mini-batch size with all tuples below to 'horse riding' activity.
    ## supervised: indicate with the labels are Pos / Neg classification in case of unsupervised or Activity Label in case of supervised

    def next(self, subset, fix_label=None,supervised = False):
        if(supervised):
            return self.supervised_next(subset, fix_label)
        else:
            return self.unsupervised_next(subset, fix_label)

def save_pkls(prefix, context,lbls,suffix):
    for i in range(context.shape[0]):
        current_cntxt = np.reshape(context[i], (const.frame_height, const.frame_width, 5))
        for j in range(5):
            plt.imshow(current_cntxt[:,:,j]);
            plt.savefig(file_const.dump_path + prefix + str(i) + '_' + str(j) + suffix+'.png')



def save_imgs(prefix, imgs,lbls,suffix):
    for i in range(imgs.shape[0]):
        cv2.imwrite(file_const.dump_path + prefix + str(i) + '_' + str(lbls[i]) + suffix+'.png',
                    np.reshape(imgs[i], (const.frame_height, const.frame_width, const.frame_channels)))


if __name__ == '__main__':

    args = dict()
    args[data_args.gen_nearby_frame] = False;
    args[data_args.data_augmentation_enabled] = False

    vdz_dataset = TupleLoader(args);
    import time
    start_time = time.time()
    words, contexts, lbls = vdz_dataset.next(const.Subset.TRAIN,1)
    elapsed_time = time.time() - start_time
    print('elapsed_time :', elapsed_time)
    ## Some visualization for debugging purpose
    save_imgs('tuple_',words,lbls,'_img');
    save_pkls('tuple_', contexts, lbls, '_pkl');
    print('Done')