import ezdxf

doc = ezdxf.new("R2010")
msp = doc.modelspace()

W, H, G = 500, 400, 50

def add_room(x0, y0, x1, y1, label):
    msp.add_lwpolyline([(x0,y0),(x1,y0),(x1,y1),(x0,y1)], close=True)
    msp.add_text(label, dxfattribs={"insert": ((x0+x1)/2, (y0+y1)/2), "height": 30})

# Top row
for i, lbl in enumerate(["3","4","5","6","8","10","11","12","14","LIFT","WASHROOM"]):
    add_room(i*(W+G), 2600, i*(W+G)+W, 3000, lbl)

# Left column
for i, lbl in enumerate(["2","1","45","44","43","42","41"]):
    add_room(0, 2100-i*(H+G), W, 2500-i*(H+G), lbl)

# Right column
for i, lbl in enumerate(["18","19","20","21","22","23","24"]):
    add_room(10*(W+G), 2100-i*(H+G), 10*(W+G)+W, 2500-i*(H+G), lbl)

# Middle rooms
for lbl, col in [("7",3),("9",4),("13",6),("15",7),("16",8),("17",9)]:
    add_room(col*(W+G), 2100, col*(W+G)+W, 2500, lbl)

# Lifts
add_room(3*(W+G), 1600, 3*(W+G)+W, 2000, "LIFT")
add_room(4*(W+G), 1600, 4*(W+G)+W, 2000, "LIFT")

# Middle bottom
for lbl, col in [("35",3),("33",4),("29",6),("27",7),("26",8),("25",9)]:
    add_room(col*(W+G), 1050, col*(W+G)+W, 1450, lbl)

# Bottom row
for i, lbl in enumerate(["40","39","38","37","36","34","31","30","28","WASHROOM"]):
    add_room(i*(W+G), 0, i*(W+G)+W, 400, lbl)

doc.saveas("vit_floors_2_17.dxf")
print("✅ DXF created successfully!")