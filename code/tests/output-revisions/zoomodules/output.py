from zoomodules import ops
import subprocess, shutil

# Remove any text of the form <title>...</title> from the input string. Return
# the new string, along with the contents of the title element.
def extract_title_element(s):
    if len(s) < 15: return (s, '')
    new_string = s
    contents = ''
    left_index = 0
    right_index = 0
    for i in range(len(s)-15):
        if s[i:i+7] == '<title>':
            left_index = i
            break
    for i in range(len(s)-8):
        if s[i:i+8] == '</title>': right_index = i
    if left_index < right_index:
        new_string = s[0:left_index]+s[right_index+8:len(s)]
        contents = s[left_index+7:right_index]
    return (new_string, contents)

# If the string s has the form <g...>..., output a string of the form
# <g... num="t">... . If s does not have this form, then return s.
def add_num_attribute(s, t):
    if s[0:2] != '<g': return s
    right_index = 0
    for i in range(len(s)):
        if s[i] == '>':
            right_index = i
            break
    if right_index == 0: return s
    new_string = s[0:right_index] + ' num="' + t + '"'  + s[right_index:len(s)]
    return new_string

# Return 'P' if x < y is proven, 'D' if it is disproven, and 'O' if it is open.
# Otherwise, return U.
def get_status_character(x, y, Rel, knowledge):
    if x == y: return 'P'
    if knowledge[('p', Rel, x, y)]: return 'P'
    if knowledge[('d', Rel, x, y)]: return 'D'
    if knowledge[('-p', Rel, x, y)] and knowledge[('-d', Rel, x, y)]:
        return 'O'
    return 'U'

def get_gradient(x, y, Rel, knowledge, op):
    '''Pick the correct gradient name for the y bubble, given that x has been
    clicked.
    '''
    if x == y: return "Sel"

    a = get_status_character(x, y, Rel, knowledge)
    b = get_status_character(op['cocap'][x], y, Rel, knowledge)
    c = get_status_character(op['co'][x], y, Rel, knowledge)
    s = a + b + c

    possibilities = ['PPP', 'PPD', 'PPO', 'PPU', 'DPP', 'DPD', 'DDD', 'DOD',
                     'DUD', 'DPO', 'DOO', 'DUO', 'DPU', 'DOU', 'DUU', 'OPP',
                     'OPD', 'OOD', 'OUD', 'OPO', 'OOO', 'OUO', 'OPU', 'OOU',
                     'OUU', 'UPP', 'UPD', 'UOD', 'UUD', 'UPO', 'UOO', 'UUO',
                     'UPU', 'UOU', 'UUU']

    if s not in possibilities: return "Err"

    return s

def isdimline(s):
    '''Check whether a string has the form <svg width="..." height="..." ...
    '''
    quote_indices=[]
    for i in range(len(s)):
        if s[i] == '"': quote_indices.append(i)
    if len(quote_indices) < 4: return False
    if s[0:quote_indices[0]] != "<svg width=": return False
    if s[quote_indices[1]-2:quote_indices[2]] != "pt\" height=": return False
    if s[quote_indices[3]-2:quote_indices[3]] != "pt": False
    m = s[quote_indices[0]+1:quote_indices[1]-2]
    n = s[quote_indices[2]+1:quote_indices[3]-2]
    if (not str.isdigit(m)) or (not str.isdigit(n)): return False
    return True

def getdimensions(s):
    '''Get the dimensions of the SVG object from the relevant line.
    '''
    q = []
    for ind in range(len(s)):
        if len(q) == 4: break
        if s[ind] == '"': q.append(ind)
    i = q[0]+1
    j = q[1]-2
    k = q[2]+1
    l = q[3]-2
    m = int(s[i:j])
    n = int(s[k:l])
    return (m,n)

def getstrend(s):
    '''Extract the end of the line specifying the dimensions of the SVG file.
    '''
    ctr = 0
    i = 0
    while ctr < 4:
        if s[i] == '"': ctr += 1
        i += 1
    return s[i:len(s)]

def writenewdims(M, N, s):
    '''Returns the line that will specify the dimensions of the SVG object in
    the new SVG file.
    '''
    t = "<svg width=\""
    t += str(M)
    t += "pt\" height=\""
    t += str(N)
    t += "pt\""
    t += s
    return t

def eqtable(d):
    '''Create an HTML table from the dict d. It is expected that the keys of d
    are strings (preferred names) and the values are sets of strings (equivalent
    names).
    '''
    table = "<table>\n  <tr>\n    <th>Preferred Name</th>\n    " \
            + "<th>Alternate Names</th>\n  </tr>\n"

    for preferred_name in sorted(d.keys()):
        row = "  <tr>\n    <td>" + preferred_name + "</td>\n"
        alternate_names = ', '.join(sorted(d[preferred_name]))
        row += "    <td>" + alternate_names + "</td>\n  </tr>\n"
        table += row

    table += "</table>"

    return table

def make_world_diagram(classes_keywords, knowledge, q, op, classes, Rel,
                       colored_graph, table_names):
    '''Create SVG file for the specified world.
    '''

    dot_filename = './data/output_' + Rel + '.dot'
    svg_filename = './data/outgraph_' + Rel + '.svg'
    gradient_filename = './zoomodules/gradients.txt'
    svg_copy_filename = './data/outgraph_original_' + Rel + '.svg'
    
    outfile = open(dot_filename, 'w')
    outfile.write('digraph G {')
    outfile.write('\n    bgcolor=white;')
    outfile.write('\n    rankdir=BT;')
    outfile.write('\n    node [color=black,fontcolor=black];')

    hidden_classes = set()
    for x in classes_keywords:
        if 'hide' in classes_keywords[x]: hidden_classes.add(q[x])

    graph_names = sorted(colored_graph.keys())
    graph_names_index = 1
    graph_numbering = {}
    for x in graph_names:
        s = '\n    ' + str(graph_names_index) + ' [label=\"' + x + '\"];'
        outfile.write(s)
        graph_numbering[x] = graph_names_index
        graph_names_index += 1

    table_dict = {}
    for x in table_names:
        table_dict[x] = set()
        for y in classes:
            if y in hidden_classes or len(y.split('.')) > 1: continue
            if x == y: continue
            if q[x] == q[y]:
                table_dict[x].add(y)
                continue
            if knowledge[('p', Rel, q[x], q[y])]:
                if knowledge[('p', Rel, q[y], q[x])]: table_dict[x].add(y)
    empty_table_entries = set()
    for x in table_dict:
        if not table_dict[x]: empty_table_entries.add(x)
    for x in empty_table_entries:
        table_dict.pop(x)
                
    for x in colored_graph:
        for color in ['black', 'blue', 'red', 'green']:
            for y in colored_graph[x][color]:
                s = '\n    ' + str(graph_numbering[x]) + ' -> '
                s += str(graph_numbering[y]) + ' [color=' + color + '];'
                outfile.write(s)

    outfile.write('\n}')
    outfile.close()

    subprocess.run(['dot', '-Tsvg', dot_filename, '-o', svg_filename])

    gradient_file = open(gradient_filename)
    gradients = []
    for line in gradient_file: gradients.append(line)
    gradient_file.close()

    svgfile = open(svg_filename)
    newsvg = []

    areafactor = 0.65
    nonewdims = True

    for line in svgfile:
        new_line = line
        if nonewdims:
            # rewrite dimensions if needed
            if isdimline(new_line):
                (m,n) = getdimensions(new_line)
                end = getstrend(new_line)
                new_line = writenewdims(m*areafactor, n*areafactor,  end)
                nonewdims = False
        (new_line, title_element) = extract_title_element(new_line)
        if title_element:
            new_line = add_num_attribute(newsvg[len(newsvg)-1], title_element)
            newsvg[len(newsvg)-1] = new_line
        elif new_line: newsvg.append(new_line)
        if new_line[0:14] == '<g id="graph0"': newsvg += gradients

    svgfile.close()

    shutil.copy(svg_filename, svg_copy_filename)
    svgfile = open(svg_filename, 'w')
    svgfile.writelines(newsvg)
    svgfile.close()

    return table_dict
    
def main(classes_keywords, knowledge, q, redundancies, names, op, classes, tclosure, props, Hasse, colored_graph, gradient_list, table_names):

    transitive_worlds = ['A', 'AA', 'R', 'T']
    table_dict ={}
    table = {}
    for Rel in transitive_worlds:
        table_dict[Rel] = make_world_diagram(classes_keywords, knowledge, q,
                                             op, classes, Rel,
                                             colored_graph[Rel],
                                             table_names[Rel])

        table[Rel] = eqtable(table_dict[Rel])
    
    redfile = open('./data/redundancies.txt', 'w')
    redfile.write('Upper bound for redundant inclusions:\n\n')

    for x in props['<']:
        for y in props['<'][x]:
            if q[y] not in Hasse[q[x]]:
                redfile.write(x + ' < ' + y + '\n')

    redfile.write('\nRedundant initial formulas:\n\n')
    redfile.write('\n'.join(redundancies))

    redfile.close()

    htmlfile = open('./data/outgraph.html', 'w')
    svgfile = open('./data/outgraph_A.svg')

    htmlfile.write("""<html>
    <head>
    <style>
    body.dark-mode {
      filter: invert(100%) hue-rotate(180deg);
      background-color: black
    }
    body.light-mode {
      filter: invert(0%);
      background-color: white
    }
    table, th, td {
        border: 2px solid black;
    }
    th {
        text-align: left;
    }
    td {
        border: 1px solid black;
    }

    text {
        cursor: pointer;
    }
    </style>
    <script>

    var coloring_A = [""")

    for i in range(len(gradient_list['A'])):
        htmlfile.write('["' + '", "'.join(gradient_list['A'][i]) + '"]')
        if i != len(gradient_list['A'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_AA = [')
    for i in range(len(gradient_list['AA'])):
        htmlfile.write('["' + '", "'.join(gradient_list['AA'][i]) + '"]')
        if i != len(gradient_list['AA'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_R = [')
    for i in range(len(gradient_list['R'])):
        htmlfile.write('["' + '", "'.join(gradient_list['R'][i]) + '"]')
        if i != len(gradient_list['R'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_T = [')
    for i in range(len(gradient_list['T'])):
        htmlfile.write('["' + '", "'.join(gradient_list['T'][i]) + '"]')
        if i != len(gradient_list['T'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')


    htmlfile.write("""window.onload = init;

    function init() {

        var ellipses = document.getElementsByTagName("ellipse");

        for(var i=0; i < ellipses.length; i++)
            ellipses[i].parentNode.addEventListener("click", colorNode, true);

        }

    function colorNode(event) {

        var ellipses = document.getElementsByTagName("ellipse");
        var iA = parseInt(event.currentTarget.getAttribute("num"));

        for(var i=0; i < ellipses.length; i++) {
    	iB = parseInt(ellipses[i].parentNode.getAttribute("num"))
            var fillValue = "url(#".concat(coloring_A[iA-1][iB-1], ")");
            ellipses[i].setAttribute("fill", fillValue)
            }

    }

    function toggleTheme() {
        var x = document.getElementById("docbody");
        if (x.className == "light-mode") {
          x.className = "dark-mode";
        }
        else {
          x.className = "light-mode";
        }
    }

    </script>

    </head>

    <body id="docbody" class="light-mode">

    <h1>Output Graph</h1>

    <button type="button" name="theme" onclick="toggleTheme()" >Toggle light/dark
    </button>

    <p>The arrows are interpreted as follows:</p>

    <ul style="list-style-type:none">
    <li>A <span style="color:black">&rarr;</span> B: A &sube; B and co(A) &sube; B
    for every oracle.</li>

    <li>A <span style="color:blue">&rarr;</span> B: A &sube; B for every oracle.
    </li>

    <li>A <span style="color:red">&rarr;</span> B: co(A) &sube; B for every oracle.
    </li>

    <li>A <span style="color:green">&rarr;</span> B: cocap(A) &sube; B for every
    oracle.</li>
    </ul>

    <p> Click on a node to compare it to other complexity classes. Clicking a node
    marks it as A, and the coloring of each node shows the status of the
    corresponding class when it is considered as B. The left part of the node shows
    the status of A &sube; B, the right part of the node shows the status of co(A)
    &sube; B, and the middle part of the node shows the status of cocap(A) &sube; B
    (all with respect to every oracle). </p>

    <p> The colors are interpreted as follows: </p>

    <ul>
    <li style="color:#00b712">Proven</li>
    <li style="color:#ff0000">Disproven</li>
    <li style="color:#b2ac00">Open</li>
    <li style="color:#848484">Unknown to the system</li>
    <li style="color:#0076ff">Currently selected</li>
    <li style="color:#ff7b00">Error: the status of this class is logically
    impossible</li>
    </ul>

    """)

    for line in svgfile: htmlfile.write(line)

    svgfile.close()

    htmlfile.write("\n<br/>\n<br/>\n")
    htmlfile.write(table['A'])
    htmlfile.write("""</body>
    </html>""")

    htmlfile.close()

    htmlfile = open('./data/outgraph.html', 'w')
    svgfile = open('./data/outgraph_A.svg')

    htmlfile.write("""<html>
    <head>
    <style>
    body.dark-mode {
      filter: invert(100%) hue-rotate(180deg);
      background-color: black
    }
    body.light-mode {
      filter: invert(0%);
      background-color: white
    }
    table, th, td {
        border: 2px solid black;
    }
    th {
        text-align: left;
    }
    td {
        border: 1px solid black;
    }

    text {
        cursor: pointer;
    }
    </style>
    <script>

    var coloring_A = [""")

    for i in range(len(gradient_list['A'])):
        htmlfile.write('["' + '", "'.join(gradient_list['A'][i]) + '"]')
        if i != len(gradient_list['A'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_AA = [')
    for i in range(len(gradient_list['AA'])):
        htmlfile.write('["' + '", "'.join(gradient_list['AA'][i]) + '"]')
        if i != len(gradient_list['AA'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_R = [')
    for i in range(len(gradient_list['R'])):
        htmlfile.write('["' + '", "'.join(gradient_list['R'][i]) + '"]')
        if i != len(gradient_list['R'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_T = [')
    for i in range(len(gradient_list['T'])):
        htmlfile.write('["' + '", "'.join(gradient_list['T'][i]) + '"]')
        if i != len(gradient_list['T'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')


    htmlfile.write("""window.onload = init;

    function init() {

        var ellipses = document.getElementsByTagName("ellipse");

        for(var i=0; i < ellipses.length; i++)
            ellipses[i].parentNode.addEventListener("click", colorNode, true);

        }

    function colorNode(event) {

        var ellipses = document.getElementsByTagName("ellipse");
        var iA = parseInt(event.currentTarget.getAttribute("num"));

        for(var i=0; i < ellipses.length; i++) {
    	iB = parseInt(ellipses[i].parentNode.getAttribute("num"))
            var fillValue = "url(#".concat(coloring_A[iA-1][iB-1], ")");
            ellipses[i].setAttribute("fill", fillValue)
            }

    }

    function toggleTheme() {
        var x = document.getElementById("docbody");
        if (x.className == "light-mode") {
          x.className = "dark-mode";
        }
        else {
          x.className = "light-mode";
        }
    }

    </script>

    </head>

    <body id="docbody" class="light-mode">

    <h1>Output Graph</h1>

    <button type="button" name="theme" onclick="toggleTheme()" >Toggle light/dark
    </button>

    <p>The arrows are interpreted as follows:</p>

    <ul style="list-style-type:none">
    <li>A <span style="color:black">&rarr;</span> B: A &sube; B and co(A) &sube; B
    for every oracle.</li>

    <li>A <span style="color:blue">&rarr;</span> B: A &sube; B for every oracle.
    </li>

    <li>A <span style="color:red">&rarr;</span> B: co(A) &sube; B for every oracle.
    </li>

    <li>A <span style="color:green">&rarr;</span> B: cocap(A) &sube; B for every
    oracle.</li>
    </ul>

    <p> Click on a node to compare it to other complexity classes. Clicking a node
    marks it as A, and the coloring of each node shows the status of the
    corresponding class when it is considered as B. The left part of the node shows
    the status of A &sube; B, the right part of the node shows the status of co(A)
    &sube; B, and the middle part of the node shows the status of cocap(A) &sube; B
    (all with respect to every oracle). </p>

    <p> The colors are interpreted as follows: </p>

    <ul>
    <li style="color:#00b712">Proven</li>
    <li style="color:#ff0000">Disproven</li>
    <li style="color:#b2ac00">Open</li>
    <li style="color:#848484">Unknown to the system</li>
    <li style="color:#0076ff">Currently selected</li>
    <li style="color:#ff7b00">Error: the status of this class is logically
    impossible</li>
    </ul>

    """)

    for line in svgfile: htmlfile.write(line)

    svgfile.close()

    htmlfile.write("\n<br/>\n<br/>\n")
    htmlfile.write(table['A'])
    htmlfile.write("""</body>
    </html>""")

    htmlfile.close()

    htmlfile = open('./data/outgraph.html', 'w')
    svgfile = open('./data/outgraph_A.svg')

    htmlfile.write("""<html>
    <head>
    <style>
    body.dark-mode {
      filter: invert(100%) hue-rotate(180deg);
      background-color: black
    }
    body.light-mode {
      filter: invert(0%);
      background-color: white
    }
    table, th, td {
        border: 2px solid black;
    }
    th {
        text-align: left;
    }
    td {
        border: 1px solid black;
    }

    text {
        cursor: pointer;
    }
    </style>
    <script>

    var coloring_A = [""")

    for i in range(len(gradient_list['A'])):
        htmlfile.write('["' + '", "'.join(gradient_list['A'][i]) + '"]')
        if i != len(gradient_list['A'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_AA = [')
    for i in range(len(gradient_list['AA'])):
        htmlfile.write('["' + '", "'.join(gradient_list['AA'][i]) + '"]')
        if i != len(gradient_list['AA'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_R = [')
    for i in range(len(gradient_list['R'])):
        htmlfile.write('["' + '", "'.join(gradient_list['R'][i]) + '"]')
        if i != len(gradient_list['R'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_T = [')
    for i in range(len(gradient_list['T'])):
        htmlfile.write('["' + '", "'.join(gradient_list['T'][i]) + '"]')
        if i != len(gradient_list['T'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')


    htmlfile.write("""window.onload = init;

    function init() {

        var ellipses = document.getElementsByTagName("ellipse");

        for(var i=0; i < ellipses.length; i++)
            ellipses[i].parentNode.addEventListener("click", colorNode, true);

        }

    function colorNode(event) {

        var ellipses = document.getElementsByTagName("ellipse");
        var iA = parseInt(event.currentTarget.getAttribute("num"));

        for(var i=0; i < ellipses.length; i++) {
    	iB = parseInt(ellipses[i].parentNode.getAttribute("num"))
            var fillValue = "url(#".concat(coloring_A[iA-1][iB-1], ")");
            ellipses[i].setAttribute("fill", fillValue)
            }

    }

    function toggleTheme() {
        var x = document.getElementById("docbody");
        if (x.className == "light-mode") {
          x.className = "dark-mode";
        }
        else {
          x.className = "light-mode";
        }
    }

    </script>

    </head>

    <body id="docbody" class="light-mode">

    <h1>Output Graph</h1>

    <button type="button" name="theme" onclick="toggleTheme()" >Toggle light/dark
    </button>

    <p>The arrows are interpreted as follows:</p>

    <ul style="list-style-type:none">
    <li>A <span style="color:black">&rarr;</span> B: A &sube; B and co(A) &sube; B
    for every oracle.</li>

    <li>A <span style="color:blue">&rarr;</span> B: A &sube; B for every oracle.
    </li>

    <li>A <span style="color:red">&rarr;</span> B: co(A) &sube; B for every oracle.
    </li>

    <li>A <span style="color:green">&rarr;</span> B: cocap(A) &sube; B for every
    oracle.</li>
    </ul>

    <p> Click on a node to compare it to other complexity classes. Clicking a node
    marks it as A, and the coloring of each node shows the status of the
    corresponding class when it is considered as B. The left part of the node shows
    the status of A &sube; B, the right part of the node shows the status of co(A)
    &sube; B, and the middle part of the node shows the status of cocap(A) &sube; B
    (all with respect to every oracle). </p>

    <p> The colors are interpreted as follows: </p>

    <ul>
    <li style="color:#00b712">Proven</li>
    <li style="color:#ff0000">Disproven</li>
    <li style="color:#b2ac00">Open</li>
    <li style="color:#848484">Unknown to the system</li>
    <li style="color:#0076ff">Currently selected</li>
    <li style="color:#ff7b00">Error: the status of this class is logically
    impossible</li>
    </ul>

    """)

    for line in svgfile: htmlfile.write(line)

    svgfile.close()

    htmlfile.write("\n<br/>\n<br/>\n")
    htmlfile.write(table['A'])
    htmlfile.write("""</body>
    </html>""")

    htmlfile.close()

    htmlfile = open('./data/outgraph.html', 'w')
    svgfile = open('./data/outgraph_A.svg')

    htmlfile.write("""<html>
    <head>
    <style>
    body.dark-mode {
      filter: invert(100%) hue-rotate(180deg);
      background-color: black
    }
    body.light-mode {
      filter: invert(0%);
      background-color: white
    }
    table, th, td {
        border: 2px solid black;
    }
    th {
        text-align: left;
    }
    td {
        border: 1px solid black;
    }

    text {
        cursor: pointer;
    }
    </style>
    <script>

    var coloring_A = [""")

    for i in range(len(gradient_list['A'])):
        htmlfile.write('["' + '", "'.join(gradient_list['A'][i]) + '"]')
        if i != len(gradient_list['A'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_AA = [')
    for i in range(len(gradient_list['AA'])):
        htmlfile.write('["' + '", "'.join(gradient_list['AA'][i]) + '"]')
        if i != len(gradient_list['AA'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_R = [')
    for i in range(len(gradient_list['R'])):
        htmlfile.write('["' + '", "'.join(gradient_list['R'][i]) + '"]')
        if i != len(gradient_list['R'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')
    htmlfile.write('var coloring_T = [')
    for i in range(len(gradient_list['T'])):
        htmlfile.write('["' + '", "'.join(gradient_list['T'][i]) + '"]')
        if i != len(gradient_list['T'])-1:
            htmlfile.write(',\n                ')
    htmlfile.write('];\n\n')


    htmlfile.write("""window.onload = init;

    function init() {

        var ellipses = document.getElementsByTagName("ellipse");

        for(var i=0; i < ellipses.length; i++)
            ellipses[i].parentNode.addEventListener("click", colorNode, true);

        }

    function colorNode(event) {

        var ellipses = document.getElementsByTagName("ellipse");
        var iA = parseInt(event.currentTarget.getAttribute("num"));

        for(var i=0; i < ellipses.length; i++) {
    	iB = parseInt(ellipses[i].parentNode.getAttribute("num"))
            var fillValue = "url(#".concat(coloring_A[iA-1][iB-1], ")");
            ellipses[i].setAttribute("fill", fillValue)
            }

    }

    function toggleTheme() {
        var x = document.getElementById("docbody");
        if (x.className == "light-mode") {
          x.className = "dark-mode";
        }
        else {
          x.className = "light-mode";
        }
    }

    </script>

    </head>

    <body id="docbody" class="light-mode">

    <h1>Output Graph</h1>

    <button type="button" name="theme" onclick="toggleTheme()" >Toggle light/dark
    </button>

    <p>The arrows are interpreted as follows:</p>

    <ul style="list-style-type:none">
    <li>A <span style="color:black">&rarr;</span> B: A &sube; B and co(A) &sube; B
    for every oracle.</li>

    <li>A <span style="color:blue">&rarr;</span> B: A &sube; B for every oracle.
    </li>

    <li>A <span style="color:red">&rarr;</span> B: co(A) &sube; B for every oracle.
    </li>

    <li>A <span style="color:green">&rarr;</span> B: cocap(A) &sube; B for every
    oracle.</li>
    </ul>

    <p> Click on a node to compare it to other complexity classes. Clicking a node
    marks it as A, and the coloring of each node shows the status of the
    corresponding class when it is considered as B. The left part of the node shows
    the status of A &sube; B, the right part of the node shows the status of co(A)
    &sube; B, and the middle part of the node shows the status of cocap(A) &sube; B
    (all with respect to every oracle). </p>

    <p> The colors are interpreted as follows: </p>

    <ul>
    <li style="color:#00b712">Proven</li>
    <li style="color:#ff0000">Disproven</li>
    <li style="color:#b2ac00">Open</li>
    <li style="color:#848484">Unknown to the system</li>
    <li style="color:#0076ff">Currently selected</li>
    <li style="color:#ff7b00">Error: the status of this class is logically
    impossible</li>
    </ul>

    """)

    for line in svgfile: htmlfile.write(line)

    svgfile.close()

    htmlfile.write("\n<br/>\n<br/>\n")
    htmlfile.write(table['A'])
    htmlfile.write("""</body>
    </html>""")

    htmlfile.close()

