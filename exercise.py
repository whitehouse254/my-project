grades={"alice":[90,95,90],
         "bob":[70,65,72],
          "charlie": [45,50,48],
          "diana": [95,100,98]}
for name,scores in grades.items():
    avg=sum(scores)/len(scores)
    if avg>=90:
       print(f"{name} smart student")
    elif avg>70:
       print(f"{name} passed")
    else:
        print(f"{name} need a tutor")
    print(f"{name} (average:{avg})")