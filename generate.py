#!/usr/bin/env python
"Code generator, part of the build process."
import os, sys
import brushsettings

def writefile(filename, s):
    "write generated code if changed"
    s = '// DO NOT EDIT - autogenerated by ' + sys.argv[0] + '\n\n' + s
    if os.path.exists(filename) and open(filename).read() == s:
        print 'Checked', filename
    else:
        print 'Writing', filename
        open(filename, 'w').write(s)


content = ''
for i in brushsettings.inputs:
    content += '#define INPUT_%s %d\n' % (i.name.upper(), i.index)
content += '#define INPUT_COUNT %d\n' % len(brushsettings.inputs)
content += '\n'
for s in brushsettings.settings:
    content += '#define BRUSH_%s %d\n' % (s.cname.upper(), s.index)
content += '#define BRUSH_SETTINGS_COUNT %d\n' % len(brushsettings.settings)
content += '\n'
for s in brushsettings.states:
    content += '#define STATE_%s %d\n' % (s.cname.upper(), s.index)
content += '#define STATE_COUNT %d\n' % len(brushsettings.states)

writefile('brushsettings.h', content)

