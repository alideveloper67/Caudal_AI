import 'package:flutter/material.dart';

import 'tema.dart';

/// Emojis a mano para los chats (el teclado del teléfono también tiene los suyos).
const emojisChat = <String, List<String>>{
  'Caras': ['😀', '😂', '🤣', '😊', '😍', '🥰', '😘', '😎', '🤩', '🥳', '😮', '😢', '😭', '😡', '🤔', '🙄',
    '😴', '🤯', '😅', '😇', '🤗', '😏', '😬', '🥺'],
  'Gestos': ['🙌', '👏', '👍', '👎', '🙏', '💪', '👋', '🤘', '✌️', '🤝', '🫶', '👀'],
  'Música': ['🎵', '🎶', '🎧', '🎤', '🎸', '🥁', '🎹', '🎺', '🎻', '🕺', '💃', '🪩'],
  'Más': ['🔥', '❤️', '💔', '💯', '🎉', '✨', '⭐', '🌙', '☀️', '🌈', '🍻', '☕'],
};

/// Abre una hoja con emojis y llama a [alElegir] con cada uno que se toque
/// (se puede elegir varios seguidos).
Future<void> elegirEmoji(BuildContext context, ValueChanged<String> alElegir) => showModalBottomSheet<void>(
      context: context,
      useRootNavigator: true,
      showDragHandle: true,
      builder: (ctx) => SafeArea(
        child: SizedBox(
          height: 320,
          child: ListView(padding: const EdgeInsets.fromLTRB(12, 0, 12, 12), children: [
            for (final e in emojisChat.entries) ...[
              Padding(
                padding: const EdgeInsets.fromLTRB(6, 8, 6, 4),
                child: Text(e.key, style: const TextStyle(fontSize: 12, fontWeight: FontWeight.w700, color: C.texto3)),
              ),
              Wrap(children: [
                for (final emoji in e.value)
                  InkResponse(
                    radius: 24,
                    onTap: () => alElegir(emoji),
                    child: SizedBox(width: 46, height: 46,
                        child: Center(child: Text(emoji, style: const TextStyle(fontSize: 26)))),
                  ),
              ]),
            ],
          ]),
        ),
      ),
    );

/// Mete [emoji] donde está el cursor de [campo].
void insertarEnCampo(TextEditingController campo, String emoji) {
  final v = campo.value;
  final ini = v.selection.isValid ? v.selection.start : v.text.length;
  final fin = v.selection.isValid ? v.selection.end : v.text.length;
  final texto = v.text.replaceRange(ini, fin, emoji);
  campo.value = TextEditingValue(text: texto, selection: TextSelection.collapsed(offset: ini + emoji.length));
}
