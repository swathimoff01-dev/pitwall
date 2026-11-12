#Problem 1 
numbers = [4, 9, 2, 9, 7]
a = numbers[0]
for i in numbers:
    if(i>a):
        a=i 
#Problem 2 
numbers = [3, 1, 3, 2, 1]
dedupe = []
for i in numbers:
    if(i not in dedupe):
        dedupe.append(i)

#Problem 3 
from Collections import Counter 

nums =[1, 2, 3, 2, 4, 1]
freq = Counter(nums)
a = dict(freq)
for key,values in a.items(): 
    if(values==1):
        nums.remove(key)


#Problem 4
nums = [1,2,4,5,6]
count = 1 
for i in nums: 
    if(i!=count):
        print(i)
    count+=1

#Problem 5 Batching no idea 