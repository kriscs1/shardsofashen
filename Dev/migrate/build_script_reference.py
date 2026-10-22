r"""Read the script language (dragonsword/script_language.py), check it, check the scripts, and write Dev\Script Commands.txt.
   Usage: python -I Dev\migrate\build_script_reference.py . "Dev\Script Commands.txt"   (run from the game folder)"""
import re, sys, os, glob

root = sys.argv[1]
sys.path.insert(0, root)
from dragonsword import script_language as L     # the script language (it used to be [SE.Get.Commands] in the .bas)
cmd = {i + 1: dict([(1, name), (2, str(len(args)))] + [(3 + k, a) for k, a in enumerate(args)])
       for i, (name, args) in enumerate(L.COMMANDS)}
var_n = {i + 1: v for i, v in enumerate(L.VARIABLES)}
ncmd = len(L.COMMANDS)
help_by = dict(L.HELP)
problems = []
cmds = []
for i in sorted(cmd):
    c = cmd[i]
    nargs = int(c[2])
    args = [c.get(3 + k, '') for k in range(nargs)]
    extra = [k for k in c if k > nargs + 2]
    if extra: problems.append('command %s has argument slots beyond its count: %s' % (c[1], extra))
    if '' in args: problems.append('command %s has an empty argument type' % c[1])
    if i > ncmd: problems.append('command %s (%d) is beyond Number.Of.Commands' % (c[1], i))
    if not help_by.get(c[1]): problems.append('no help for command ' + c[1])
    for a in args:
        if not help_by.get(a): problems.append('no help for argument %s (%s)' % (a, c[1]))
    cmds.append((c[1], args))
names = {c for c, a in cmds}
print('commands', len(cmds), 'Number.Of.Commands', ncmd)
for p in problems: print('PROBLEM', p)

# check the scripts
for f in sorted(glob.glob(os.path.join(root, 'Data', 'Scripts', '*.txt'))):
    lines = [l for l in open(f, encoding='latin-1').read().splitlines() if l.strip() and not l.strip().startswith('//')]
    n = len(lines)
    for idx, l in enumerate(lines, 1):
        parts = l.split('\t')
        if int(parts[0]) != idx: print(os.path.basename(f), 'line number mismatch', l)
        c = parts[1]
        if c not in names:
            print(os.path.basename(f), 'unknown command', c); continue
        args = dict(cmds)[c]
        if len(parts) - 2 > len(args): print(os.path.basename(f), 'too many args', l)
        for a, v in zip(args, parts[2:]):
            if 'GOTO LINE' in a and v.strip() and not (v.strip().isdigit() and 1 <= int(v) <= n):
                print(os.path.basename(f), 'bad goto', l)

if len(sys.argv) > 2:
    out = []
    w = out.append
    w('Dragon Sword v2 - Script Commands')
    w('=================================')
    w('')
    w('Generated from dragonsword/script_language.py, which defines the script language.')
    w('Do not rename commands or change their arguments: the game implements exactly this list.')
    w('(Help texts below are the ones shown when you right-click a cell in the Script Editor;')
    w('a "|" in a help text is a line break.)')
    w('')
    w('FILE FORMAT')
    w('-----------')
    w('* Scripts are Data\\Scripts\\<Name>.txt. File names may contain spaces, commas and brackets,')
    w('  e.g. "Chop Tree.txt", "1,1,0.txt", "Pickup [MapItem].txt".')
    w('* One command per line:  NN<TAB>Command<TAB>arg1<TAB>arg2...   (NN = 2-digit line number, 01, 02...)')
    w('* An empty argument is written as a single space so the tabs don\'t run together.')
    w('  Some arguments use "-" for "none" (ENTITY MISC, RACK ID for the BANK).')
    w('* Lines starting with // are comments (the editor keeps them at the top of the file).')
    w('* Commands starting with ">" are conditions. Their last argument is the line to jump to if the')
    w('  condition is NOT met; if it is met the script continues on the next line.')
    w('* GOTO LINE arguments are line numbers (NN). The editor renumbers them when lines are inserted,')
    w('  deleted or moved, and warns on save about gotos to lines that don\'t exist, a missing End,')
    w('  and unknown commands.')
    w('* A script ends at an End line (there can be several).')
    w('* An empty script file counts as "not found".')
    w('')
    w('SCRIPT LOOKUP (from Dev\\Data Formats.md)')
    w('---------------------------------------')
    w('When the player does Verb on an entity/tile Name of type Type, the game runs the first that exists:')
    w('  1. "Verb Name.txt" (e.g. "Chop Tree001.txt", then without the digits, "Chop Tree.txt")')
    w('  2. "Verb [Type].txt" (e.g. "Pickup [MapItem].txt", "Drop [InventoryItem].txt")')
    w('  3. the engine\'s built-in default for that verb (Pickup, Drop, Examine, Eat, Talk to, Attack, Walk here)')
    w('* Using one item on another: "Use A With B.txt", then "Use B With A.txt".')
    w('* Triggers: the script name stored in the map (Trigger<TAB>ScriptName<TAB>TileX<TAB>TileY).')
    w('* Map entry: a script named after the map, e.g. "1,1,0.txt".')
    w('* Empty script files count as "not found".')
    w('')
    w('VARIABLES')
    w('---------')
    w('These can be used inside arguments; the game replaces them with their values.')
    w('"Variable.n$" (no $ prefix) as the SAVE AS argument of Get.Value names the variable to store into;')
    w('read it back as $Variable.n.')
    for i in sorted(var_n):
        nm, d = var_n[i]
        w('  %-26s %s' % (nm, d))
    w('')
    w('COMMANDS (%d)' % len(cmds))
    w('------------')
    w('Format:  Command  ARG 1 | ARG 2 | ...')
    w('')
    for c, args in sorted(cmds, key=lambda x: x[0].lower()):
        w('%s%s' % (c, ('    ' + ' | '.join(args)) if args else '    (no arguments)'))
        w('    ' + help_by.get(c, '').replace('|', '\n    '))
        for k, a in enumerate(args, 1):
            w('    %d. %s: %s' % (k, a, help_by.get(a, '').replace('|', '\n         ')))
        w('')
    open(sys.argv[2], 'w', encoding='latin-1', newline='\r\n').write('\n'.join(out) + '\n')
    print('wrote', sys.argv[2])
