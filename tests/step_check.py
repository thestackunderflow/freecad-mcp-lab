# Run as `freecadcmd step_check.py` (the -c form crashes freecadcmd 1.1.4 here): re-read a STEP file with OpenCASCADE and print its size and volume as one JSON line.
import json, os
import Part
s = Part.Shape()
s.read(os.environ['STEP_FILE'])
b = s.BoundBox
print('STEP_CHECK ' + json.dumps({'file': os.environ['STEP_FILE'], 'size': [b.XLength, b.YLength, b.ZLength],
                                  'min': [b.XMin, b.YMin, b.ZMin], 'volume': s.Volume, 'solids': len(s.Solids)}))
