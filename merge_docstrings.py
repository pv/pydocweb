#!/usr/bin/env python
import lxml.etree as etree
import subprocess, optparse, sys, tempfile

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

    ids2 = {}
    for el2 in tree2.getroot():
        ids2[el2.attrib['id']] = el2
    ids3 = {}
    for el3 in tree3.getroot():
        ids3[el3.attrib['id']] = el3

    for el1 in tree1.getroot():
        if el1.text is None:
            el1.text = ""
        else:
            el1.text = el1.text.strip()
        
        el2 = ids2.get(el1.attrib['id'])
        el3 = ids3.get(el1.attrib['id'])
        
        if el2 is not None: del ids2[el1.attrib['id']]
        if el3 is not None: del ids3[el1.attrib['id']]

        if el2 is None or el3 is None: continue

        if el2.text is None:
            el2.text = ""
        else:
            el2.text = el2.text.strip()

        if el3.text is None:
            el3.text = ""
        else:
            el3.text = el3.text.strip()

        if el3.text == el2.text: continue
        if el3.text == el1.text: continue
        if el2.text == el1.text:
            # no-op silent merge
            el1.text = el3.text
            continue

        new_text, conflict = merge_3way(el1.text, el2.text, el3.text)
        if conflict:
            print >> sys.stderr, "CONFLICT", el1.attrib['id']
        else:
            print >> sys.stderr, "MERGE", el1.attrib['id']
        el1.text = new_text.strip()

    if ids3.keys():
        print >> sys.stderr, "LEFTOVERS:", " ".join(ids3.keys())

    print "<?xml version=\"1.0\"?>"
    tree1.write(sys.stdout)

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
