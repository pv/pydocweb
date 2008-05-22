#!/usr/bin/env python
import lxml.etree as etree
import subprocess, optparse, sys

def main():
    p = optparse.OptionParser(usage="""%prog FILE1.xml FILE2.xml FILE3.xml

Output changes between FILE2.xml and FILE3.xml applied to FILE1.xml
""")
    options, args = p.parse_args()

    if len(args) != 3:
        p.error("Wrong number of arguments")

    tree1 = etree.parse(open(args[0], 'r'))
    tree2 = etree.parse(open(args[1], 'r'))
    tree3 = etree.parse(open(args[2], 'r'))

    for el1 in tree1.getroot():
        el2 = tree2.get(el1.attrib['id'])
        el3 = tree2.get(el1.attrib['id'])
        if el2 is None or el3 is None: continue
        if el3.text == el2.text: continue
        if el3.text == el1.text: continue

        if el1.text is None: el1.text = ""
        if el2.text is None: el2.text = ""
        if el3.text is None: el3.text = ""

        new_text, conflict = merge_3way(el1.text, el2.text, el3.text)
        if conflict:
            print >> sys.stderr, "CONFLICT", el1.attrib['id']
        el1.text = new_text

def merge_3way(base, file1, file2):
    """
    Perform a 3-way merge, inserting changes between base and file1 to file2.
    
    Returns
    -------
    out : str
        Resulting new file1, possibly with conflict markers
    conflict : bool
        Whether a conflict occurred in merge.
    
    """
    f1 = tempfile.NamedTemporaryFile()
    f2 = tempfile.NamedTemporaryFile()
    f3 = tempfile.NamedTemporaryFile()
    f1.write(file2)
    f2.write(base)
    f3.write(file1)
    f1.flush()
    f2.flush()
    f3.flush()

    p = subprocess.Popen(['merge', '-p',
                          '-L', 'web version',
                          '-L', 'old svn version',
                          '-L', 'new svn version',
                          f1.name, f2.name, f3.name],
                         stdout=subprocess.PIPE)
    out, err = p.communicate()
    
    if p.returncode != 0:
        return out, True
    return out, False


if __name__ == "__main__": main()
