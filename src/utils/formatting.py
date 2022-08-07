import discord
from itertools import chain



def plural_suffix(val: int) -> str:
    if val!=1:
        return "s"
    return ""


def informative_user_mention(user_or_member, fallback_id: int = None, separator="\n") -> str:
    id = fallback_id if fallback_id else (user_or_member.id if user_or_member else 0)
    result = f"<@{id}>{separator}"
    if user_or_member:
        if isinstance(user_or_member, discord.Member) and user_or_member.nick:
            result += user_or_member.nick + separator
        result += f"{user_or_member.name}#{user_or_member.discriminator}{separator}"
    else:
        result += "<Unknown>" + separator
    result += f"`{id}`"
    return result


def split_string_into_chunks(text: str, chunk_size: int) -> list:
    return [text[i:i+chunk_size] for i in range(0, len(text), chunk_size)]


def make_table_string(
    rows,
    *,
    headers = None,
    header_alignment: str = "5",
    column_alignment: str = "4|7",
    max_cell_content_width: int = None,
    vertical_padding: int = 0,
    horizontal_padding: int = 1,
    vertical_grid_lines: bool = True,
    horizontal_grid_lines: bool = True,
    show_row_numbers: bool = False,
    row_number_column_name: str = "Row",
    initial_row_number: int = 0,
    string_quotes: str = "\""
) -> str:
    """Alignments: string, where each number specifies the alignment of a column, separated by control characters.
    Format = "<row number alignment>|<leftmost columns alignment>;<default alignment>;<rightmost column alignments>"
    Default alignment must be specified, the rest is optional.
    Interpretted in this order: <default>, <left>;<default>, <left>;<default>;<right>
    The number specifying an alignment can be thought of as the direction on a numpad where 5 is the center.
    """
    
    if not rows and not headers:
        return "\n"
    
    def parse_alignment_format(to_parse: str) -> tuple:
        result = [None, [], None, []]
        
        halves = to_parse.split("|")
        if len(halves) > 2:
            raise ValueError("Invalid alignment format - multiple '|' characters found!")
        elif len(halves) == 2:
            #row number alignment is specified
            if len(halves[0]) > 1:
                #multiple chars in row number alignment = invalid
                raise ValueError("Invalid alignment format - multiple characters for row number alignment found!")
            elif len(halves[0]) == 1:
                #exactly one row alignment found = correct
                if halves[0] != "0":
                    #0 means unspecified
                    result[0] = int(halves[0])
            main_portion = halves[1]
        else:
            #no row number alignment specified, parse the rest as-is
            main_portion = to_parse
        
        segments = main_portion.split(";")
        
        if len(segments) > 3:
            raise ValueError("Invalid alignment format - invalid number of sections!")
        elif len(segments) == 1:
            left_segment = ""
            middle_segment = segments[0]
            right_segment = ""
        elif len(segments) == 2:
            left_segment = segments[0]
            middle_segment = segments[1]
            right_segment = ""
        else:
            left_segment = segments[0]
            middle_segment = segments[1]
            right_segment = segments[2]
        
        if len(middle_segment) != 1:
            raise ValueError("Invalid alignment format - a single default alignment value needs to be provided!")
        if middle_segment == "0":
            raise ValueError("Invalid alignment format - default alignment cannot be set to 0!")
        result[2] = int(middle_segment)
        
        for ch in left_segment:
            result[1].append(int(ch))
        for ch in right_segment:
            result[3].append(int(ch))
        
        return tuple(result)
    
    
    has_headers = True
    if not headers: #checks none and empty
        has_headers = False
    else:
        parsed_header_alignment = parse_alignment_format(header_alignment)
    parsed_column_alignment = parse_alignment_format(column_alignment)
    
    column_widths = []
    data = []
    for r, row in enumerate(chain([headers] if has_headers else [], rows)):
        is_header = has_headers and r==0
        
        maybe_row_num = []
        if show_row_numbers:
            if is_header:
                maybe_row_num.append(row_number_column_name)
            else:
                maybe_row_num.append(r-int(has_headers)+initial_row_number)
        
        data_row = []
        for c, col in enumerate(chain(maybe_row_num, row)):
            data_col = str(col)
            
            if not is_header and isinstance(col, str):
                data_col = string_quotes + data_col + string_quotes
            
            if max_cell_content_width:
                data_col = split_string_into_chunks(data_col, max_cell_content_width)
            else:
                data_col = [data_col]
            
            if c >= len(column_widths):
                column_widths.append(len(data_col[0]))
            else:
                column_widths[c] = max(column_widths[c], len(data_col[0]))
            
            data_row.append(data_col)
        data.append(data_row)
    
    result = ""
    
    
    def make_separation_line(sep: str = "-") -> str:
        if vertical_grid_lines:
            return "+" + ("+".join(sep*(col+horizontal_padding*2) for col in column_widths)) + "+\n"
        else:
            return (sep*horizontal_padding).join(sep*col for col in column_widths) + "\n"
    
    
    def aligned_cell_content(content: str, target_width: int, align: int) -> str:
        if len(content) == 0:
            return " "*target_width
        remaining_space = target_width-len(content)
        if align%3 == 1:
            return content + (remaining_space*" ")
        if align%3 == 0:
            return (remaining_space*" ") + content
        left = remaining_space//2
        right = remaining_space-left
        return (left*" ") + content + (right*" ")
    
    
    def get_alignment(row_num: int, column_num: int) -> int:
        alignments = parsed_header_alignment if has_headers and row_num==0 else parsed_column_alignment
        if show_row_numbers:
            if column_num == 0:
                return alignments[0] if alignments[0] is not None else alignments[2]
            
            column_num -= 1
            column_count = len(column_widths)-1
        else:
            column_count = len(column_widths)
            
        if column_num < len(alignments[1]):
            return alignments[1][column_num] if alignments[1][column_num] !=0 else alignments[2]
        
        back_idx = column_num - (column_count-len(alignments[3]))
        if back_idx >= 0 and alignments[3][back_idx] != 0:
            return alignments[3][back_idx]
        
        return alignments[2]
        
    
    def make_cell_content_lines(row_num: int) -> str:
        row_data = data[row_num]
        total_lines = 0
        cells = []
        for column in row_data:
            total_lines = max(total_lines, len(column))
            
        for col, width in enumerate(column_widths):
            cell = []
            empty_line = " "*width
            add_empty_lines = lambda n: cell.extend([empty_line]*n)
            
            if col < len(row_data):
                alignment = get_alignment(row_num, col)
                shift = 0
                if (alignment-1)//3 == 0:
                    #alignment = down
                    shift = total_lines-len(row_data[col])
                elif (alignment-1)//3 == 1:
                    #alignment = middle
                    shift = (total_lines-len(row_data[col]))//2
                #else: alignment = top = default
                    
                for i in range(total_lines):
                    shifted = i-shift
                    if shifted >= 0 and shifted < len(row_data[col]):
                        cell.append(aligned_cell_content(row_data[col][shifted], width, alignment))
                    else:
                        cell.append(empty_line)
            else:
                #empty column
                add_empty_lines(total_lines)
            
            cells.append(cell)
        
        result = ""
        for i in range(total_lines):
            if vertical_grid_lines:
                result += "|" + " "*horizontal_padding + (" "*horizontal_padding+"|"+" "*horizontal_padding).join(
                    cell[i] for cell in cells
                ) + " "*horizontal_padding + "|\n"
            else:
                result += (" "*horizontal_padding).join(cell[i] for cell in cells) + "\n"
        
        return result
    
    
    padding_lines = ""
    if vertical_padding > 0:
        if vertical_grid_lines:
            padding_lines = "|" + ("|".join(" "*(col+horizontal_padding*2) for col in column_widths)) + "|\n"
        else:
            padding_lines = (" "*horizontal_padding).join(" "*col for col in column_widths) + "\n"
        padding_lines = padding_lines*vertical_padding
    
    
    if horizontal_grid_lines:
        separation_line = make_separation_line("-")
        separation_line_thick = make_separation_line("=")
        
        return separation_line + padding_lines + (
            (
                #header
                (make_cell_content_lines(0) + padding_lines + separation_line_thick + padding_lines) if has_headers else ""
            ) + (
                #content
                (padding_lines + separation_line + padding_lines).join(
                    make_cell_content_lines(i) for i in range(int(has_headers), len(data))
                )
            )
        ) + padding_lines + separation_line
    
    return padding_lines.join(make_cell_content_lines(i) for i in range(len(data)))
