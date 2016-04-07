#!/usr/bin/env python

import os
import re
import subprocess as sc


DEBUG = False
TMPL_WIN = "/etc/huayra/grub/windows.tmpl"
TMPL_RECU = "/etc/huayra/grub/recuperacion.tmpl"

if not os.path.isfile(TMPL_WIN):
    TMPL_WIN = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                            "tmpl/windows.tmpl")

if not os.path.isfile(TMPL_RECU):
    TMPL_RECU = os.path.join(os.path.abspath(os.path.dirname(__file__)),
                             "tmpl/recuperacion.tmpl")


def linux_boot_prober(partition, kernel_icontains=''):
    """
    devuelve el output de `linux-boot-prober partition`.
    params: none
    returns: list
    """
    if DEBUG:
        with open('lbp-output.txt','r') as lbp:
            lbp_output = lbp.readlines()
    else:
        lbp_output = sc.check_output("linux-boot-prober {}".format(partition), shell=True).split("\n")

    lbp_output = filter(lambda x: x, lbp_output)

    if kernel_icontains:
        return filter(lambda x: kernel_icontains in x, lbp_output)
    else:
        return lbp_output


def blkid():
    """
    devuelve el output de `blkid`.
    params: none
    returns: list
    """
    if DEBUG:
        with open('blkid-output.txt','r') as blk:
            blkid_output = blk.readlines()
    else:
        blkid_output = sc.check_output("blkid", shell=True).split("\n")

    return filter(lambda x: x, blkid_output)


def lbp_to_dict(lbp_output):
    """
    le da formato al output de `linux-boot-prober`.
    params: list
    returns: list of dicts
    """

    lbp_list = []
    for line in lbp_output:
        root, boot, label, kernel, initrd, kparams = line.replace('\n','').split(':')

        lbp_list.append({
            'root': root,
            'boot': boot,
            'label': label,
            'kernel': kernel,
            'initrd': initrd,
            'kparams': kparams
        })

    return lbp_list

def blkid_to_dict(blkid_output):
    """
    le da formato al output de `blkid`.
    params: list
    returns: list of dict
    """
    regex_root = '(?P<root>.+): '
    regex_num = '([^\d+])'
    regex_sectype = '(SEC_TYPE="(?P<sectype>.[^"]+)")?( )?'
    regex_label = '(LABEL="(?P<label>.[^"]+)")?( )?'
    regex_uuid = '(UUID="(?P<uuid>.[^"]+)")?( )?'
    regex_type = '(TYPE="(?P<type>.[^"]+)")?'
    regex_blkid = regex_root + regex_label + regex_sectype + regex_uuid + regex_type

    tmp = []
    for blk in blkid_output:
        tmp.append(re.search(regex_blkid, blk))

    blkid_dict = {}
    for res in tmp:

        gpt = int(re.sub(regex_num, '', res.group('root')))

        blkid_dict[res.group('root')] = {'root': res.group('root'),
                                         'gpt': "gpt%d" % gpt,
                                         'label': res.group('label'),
                                         'sectype': res.group('sectype'),
                                         'uuid': res.group('uuid'),
                                         'type': res.group('type')}

    return blkid_dict


def filter_blkid(blkid=None, key='', value=''):
    """
    genera templates para grub
    params: str, str, str, str
    returns: str
    """

    data = {}
    if blkid and key and value:
        for root in blkid:
            if blkid.get(root).get(key) == value:
                data = blkid.get(root)

    return data


def gen_template(tmpl_name="", blkid=None, linux_boot_prober=None):
    """
    genera templates para grub
    params: str, str, str, str
    returns: str
    """

    tmpl = ""
    if tmpl_name and blkid:
        if len(blkid):
            if linux_boot_prober:
                if type(linux_boot_prober) == type([]):
                    linux_boot_prober = linux_boot_prober[0]
                blkid.update(linux_boot_prober)

            tmpl_file = open(tmpl_name, 'r')
            tmpl = ''.join(tmpl_file.readlines())
            tmpl_file.close()

            tmpl = tmpl.format(**blkid)
            tmpl = tmpl.replace('OPENBRACKET', '{')
            tmpl = tmpl.replace('CLOSEBRACKET', '}')

    return tmpl


def main():
    """
    lee la salida de blkid, parsea los datos y genera los templates.
    params: nil
    returns: nil
    """
    blkid_output = blkid()
    blkid_output = blkid_to_dict(blkid_output)

    blkid_win = filter_blkid(blkid_output, 'type', 'vfat')

    blkid_recu = filter_blkid(blkid_output, 'label', 'RECUPERACION')
    lbp_recu = lbp_to_dict(linux_boot_prober(blkid_recu.get('root'), '/boot/vmlinuz'))

    tmpl_win = gen_template(TMPL_WIN, blkid_win)
    tmpl_recu = gen_template(TMPL_RECU, blkid_recu, lbp_recu)

    print tmpl_win
    print tmpl_recu


if __name__ == "__main__":
    if os.getuid() == 0:
        main()
