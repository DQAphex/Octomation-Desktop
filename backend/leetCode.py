class Solution(object):
    def myAtoi(self, s):
        no_white_spaces = ""
        stop = False
        lastChar = ""
        for i in s:
            print(f"_{i}_",f"_{lastChar}_")
            if i == " ":
                lastChar = i
            else:
                stop = True
            if lastChar == " ":
                if i != lastChar:
                    stop = True
            if stop:
                no_white_spaces += i

        print(no_white_spaces)

        numbers = ""
        result = 0
        sign = 1

        if no_white_spaces == "":
            return 0

        gotSign = False

        if no_white_spaces[0] == "-":
            sign = -1
            no_white_spaces = no_white_spaces.replace("-","")
            gotSign = True

        if gotSign == False and no_white_spaces[0] == "+":
            sign = 1
            no_white_spaces = no_white_spaces.replace("+","")

        for i in range(len(no_white_spaces)):
            if no_white_spaces[i].isdigit():
                numbers += no_white_spaces[i]
            else: 
                numbers = numbers if numbers != "" else 0
                break

        for digit in range(len(str(numbers))):
            number_from_string = ord(str(numbers)[digit]) - ord('0')
            print(number_from_string, digit, str(numbers)[digit])
            print(result,10 ** (len(str(numbers))-digit))
            result = result + number_from_string * (10 ** (len(str(numbers))-(digit+1)))
            print(result)
        
        if result.bit_length() > 31:
            if sign > 0:
                result = (2**31) - 1 
            else:
                result = (2**31) 
        return result * sign
            


c = Solution()
c.myAtoi("  +  413")