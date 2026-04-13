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
    highest_score = 0
    highest_student = ""
    for score in scores:
        if score > highest_score:
            highest_score = score
            highest_student = name
print(f"Highest score: {highest_score} which is {highest_student}")