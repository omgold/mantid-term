#define _GNU_SOURCE

#include <stdio.h>
#include <string.h>
#include <glib.h>
#include <vte/vte.h>


typedef struct {
    gchar* text;
    GArray* attributes;
} text_segment;


static text_segment get_segment(VteTerminal* vte, glong start_row, glong start_col,
                            glong end_row, glong end_col) {
    text_segment s;
    s.attributes = g_array_new(FALSE, FALSE, sizeof(VteCharAttributes));
    s.text = vte_terminal_get_text_range(vte, start_row, start_col, end_row, end_col,
                                         NULL, NULL, s.attributes);
    return s;
}

static void free_segment(text_segment s) {
    g_free(s.text);
    g_array_free(s.attributes, TRUE);
}


gchar* get_line(VteTerminal* vte, glong row, GArray** attributes) {
    const glong step = 50;

    GArray* segments = g_array_new(FALSE, FALSE, sizeof(text_segment));

    glong start_index;
    glong end_index;
    glong text_len = 0;

    glong iter_row = row;
    while(1) {
        text_segment segment = get_segment(vte, iter_row-step, 0, iter_row, 0);
        g_array_prepend_val(segments, segment);
        gchar* pos = (gchar*)memrchr(segment.text, '\n', segment.attributes->len);
        if (pos == NULL) {
            text_len += segment.attributes->len;
            if (iter_row == 0) {
                start_index = 0;
                break;
            }
            iter_row -= step;
            iter_row = iter_row>=0?iter_row:0;
            continue;
        }
        start_index = pos - segment.text + 1;
        text_len += segment.attributes->len - start_index;
        break;
    }

    iter_row = row;
    while(1) {
        text_segment segment = get_segment(vte, iter_row, 0, iter_row+step, 0);
        g_array_append_val(segments, segment);
        if (segment.attributes->len == 0) {
            end_index = 0;
            break;
        }
        gchar* pos = (gchar*)memchr(segment.text, '\n', segment.attributes->len);
        if (pos != NULL) {
            end_index = pos - segment.text;
            text_len += end_index;
            break;
        }
        text_len += segment.attributes->len;
        iter_row += step;
    }

    gchar* text = g_new(gchar, text_len+1);
    text[text_len] = 0;
    GArray* res_attrs = g_array_sized_new(FALSE, FALSE,
                                          sizeof(VteCharAttributes), text_len);
    //g_array_set_size(attributes, 0);

    glong segment_count = segments->len;
    glong pos = 0;
    for(glong i=0; i<segment_count; i++) {
        text_segment s = g_array_index(segments, text_segment, i);
        glong segment_len;
        glong segment_start;
         if (i==0) {
             segment_start = start_index;
             segment_len = s.attributes->len-start_index;
         } else if (i==segment_count-1) {
             segment_start = 0;
             segment_len = end_index;
         } else {
             segment_start = 0;
             segment_len = s.attributes->len;
         }
         memcpy(text+pos, s.text+segment_start, segment_len);
         pos += segment_len;
         for (glong i=0; i<segment_len; i++)
             g_array_append_val(res_attrs,
                                g_array_index(s.attributes, VteCharAttributes,
                                              i+segment_start));
         free_segment(s);
    }

    g_array_free(segments, TRUE);

    *attributes = res_attrs;
    return text;
}


gboolean match_regexp(VteTerminal* vte, GRegex* regexp,
                      glong row, glong col,
                      gboolean backward, gboolean at_end,
                      glong* match_row, glong* match_col) {
    GArray* attributes;
    gchar* text = get_line(vte, row, &attributes);
    glong text_len = attributes->len;
    glong cursor_pos;
    if (!backward)
        cursor_pos = -1;
    else
        cursor_pos = text_len+1;
    for(glong i=0; i<text_len;i++) {
        VteCharAttributes a = g_array_index(attributes, VteCharAttributes, i);
        if (a.row > row) {
            cursor_pos = i;
            break;
        }
        if (a.row == row && a.column == col) {
            cursor_pos = i;
            break;
        }
    }

    GMatchInfo* match;
    gboolean success = g_regex_match(regexp, text, 0, &match);
    success = g_match_info_matches(match);

    gint match_pos = -1;

    while (g_match_info_matches(match)) {
        gint pos, start, end;
        gboolean success = g_match_info_fetch_pos(match,0, &start, &end);
        printf("s: %i %i %i\n",success, start, end);
        // print(match.fetch(0),fetch_pos.__class__)
        if (!at_end)
            pos = start;
        else
            pos = end;
        if (!backward) {
            if (pos > cursor_pos) {
                match_pos = pos;
                break;
            }
        } else {
            printf("c: %i %i\n",pos,cursor_pos);
            if (pos >= cursor_pos)
                break;
            else
                match_pos = pos;
        }
        g_match_info_next(match, NULL);
    }

    printf("m: %i %i\n",success, match_pos);

    g_match_info_free(match);

    gboolean ret;
    if (match_pos!=-1) {
        if (text_len == 0) {
            *match_row = row;
            *match_col = 0;
            ret=TRUE;
        } else {
            if (match_pos == text_len) {
                glong cols = vte_terminal_get_column_count(vte);
                VteCharAttributes match_attrs =
                    g_array_index(attributes, VteCharAttributes, match_pos-1);
                glong row = match_attrs.row;
                glong col = match_attrs.column + 1;
                if (col == cols) {
                    col = 0;
                    row++;
                }
                *match_row = row;
                *match_col = col;
            } else {
                VteCharAttributes match_attrs =
                    g_array_index(attributes, VteCharAttributes, match_pos);
                *match_row = match_attrs.row;
                *match_col = match_attrs.column;
            }
        }
        ret=TRUE;
    } else {
        *match_row = *match_col = -1;
        ret=FALSE;
    }

    g_free(text);
    g_array_free(attributes, TRUE);

    return ret;
}
