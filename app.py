from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room
from database import get_db, init_db, Room, Player, Answer
import uuid
import random
import os
from sqlalchemy import delete

app = Flask(__name__)
app.config['SECRET_KEY'] = 'adedonha-secret-key-2024'
socketio = SocketIO(app, cors_allowed_origins="*")

# Inicializar banco de dados
try:
    init_db()
    print('✓ Banco de dados conectado')
except Exception as e:
    print(f'❌ Erro ao conectar ao banco: {e}')
    print('Execute: python init_db.py')

# Letras disponíveis
AVAILABLE_LETTERS = list('ABCDEFGHIJLMNOPQRSTUVZ')

# Countdown agora é feito apenas no cliente

# Categorias padrão
DEFAULT_CATEGORIES = ['Nome', 'Animal', 'Cidade', 'Objeto', 'Cor', 'Comida']

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/room/<room_id>')
def room(room_id):
    return render_template('room.html', room_id=room_id)

# ==================== SOCKET.IO EVENTS ====================

@socketio.on('connect')
def handle_connect():
    print(f'Cliente conectado: {request.sid}')

@socketio.on('join_socketio_room')
def handle_join_socketio_room(data):
    room_id = data.get('room_id')
    player_name = data.get('player_name')  # Nome do jogador para identificação
    
    if room_id:
        db = get_db()
        try:
            room = db.query(Room).filter(Room.room_id == room_id).first()
            if room:
                new_player_id = request.sid
                
                # Verificar se este session ID já existe
                existing_player = db.query(Player).filter(Player.player_id == new_player_id).first()
                
                if not existing_player and player_name:
                    # Procurar jogador pelo NOME na sala
                    player_by_name = db.query(Player).filter(
                        Player.room_id == room_id,
                        Player.name == player_name
                    ).first()
                    
                    if player_by_name:
                        old_player_id = player_by_name.player_id
                        
                        if old_player_id != new_player_id:
                            print(f'🔄 Reconectando jogador {player_name}: {old_player_id} → {new_player_id}')
                            
                            # Atualizar player_id
                            player_by_name.player_id = new_player_id
                            
                            # Se era o host, atualizar também na sala
                            if player_by_name.is_host:
                                room.host_id = new_player_id
                                print(f'  ✓ Host atualizado para {new_player_id}')
                            
                            # Atualizar TODAS as respostas antigas deste jogador (todas as rodadas)
                            updated_answers = db.query(Answer).filter(
                                Answer.room_id == room_id,
                                Answer.player_id == old_player_id
                            ).update({'player_id': new_player_id}, synchronize_session=False)
                            
                            if updated_answers > 0:
                                print(f'  ✓ {updated_answers} respostas atualizadas')
                            
                            db.commit()
                            
                            # Notificar o cliente sobre a atualização do seu ID
                            emit('player_reconnected', {
                                'player': get_player_data(new_player_id, db),
                                'room': get_room_data(room_id, db)
                            })
                            
                            # Notificar TODOS os jogadores da sala sobre a atualização
                            emit('players_updated', {
                                'players': get_room_players(room_id, db)
                            }, room=room_id)
                    else:
                        # Jogador não encontrado pelo nome, pode ser um novo jogador entrando
                        print(f'ℹ️ Novo jogador ou jogador não encontrado: {player_name}')
            
            join_room(room_id)
            print(f'Cliente {request.sid} entrou na sala Socket.IO: {room_id}')
        except Exception as e:
            print(f'Erro ao entrar na sala Socket.IO: {e}')
            db.rollback()
        finally:
            db.close()

@socketio.on('disconnect')
def handle_disconnect():
    # NÃO fazer nada no disconnect imediato
    # Isso evita deletar a sala quando o usuário é redirecionado
    print(f'Cliente desconectado: {request.sid} (ignorando por enquanto)')

@socketio.on('leave_room_properly')
def handle_leave_room_properly(data):
    """Chamado quando o jogador realmente quer sair da sala"""
    db = get_db()
    player_id = request.sid
    
    try:
        player = db.query(Player).filter(Player.player_id == player_id).first()
        
        if player:
            room_id = player.room_id
            player_name = player.name
            was_host = player.is_host
            
            # Remover jogador
            db.delete(player)
            db.commit()
            
            # Verificar jogadores restantes
            remaining_players = db.query(Player).filter(Player.room_id == room_id).all()
            
            if not remaining_players:
                # Deletar sala e respostas
                db.query(Room).filter(Room.room_id == room_id).delete()
                db.query(Answer).filter(Answer.room_id == room_id).delete()
                db.commit()
                print(f'Sala {room_id} deletada (sem jogadores)')
            else:
                # Transferir host se necessário
                if was_host:
                    new_host = remaining_players[0]
                    new_host.is_host = True
                    db.commit()
                    
                    emit('host_changed', {
                        'new_host_id': new_host.player_id,
                        'new_host_name': new_host.name
                    }, room=room_id)
                
                # Notificar outros jogadores
                emit('player_left', {
                    'player_id': player_id,
                    'player_name': player_name,
                    'players': get_room_players(room_id, db)
                }, room=room_id)
    
    except Exception as e:
        print(f'Erro ao sair da sala: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('create_room')
def handle_create_room(data):
    db = get_db()
    try:
        player_name = data['player_name']
        room_id = str(uuid.uuid4())[:8].upper()
        player_id = request.sid
        
        # Criar sala
        new_room = Room(
            room_id=room_id,
            host_id=player_id,
            game_state='waiting',
            current_round=0,
            current_letter='',
            categories=','.join(DEFAULT_CATEGORIES)
        )
        db.add(new_room)
        
        # Criar jogador
        new_player = Player(
            player_id=player_id,
            room_id=room_id,
            name=player_name,
            score=0.0,
            is_host=True
        )
        db.add(new_player)
        
        db.commit()
        
        # Verificar se foi salvo
        verify_room = db.query(Room).filter(Room.room_id == room_id).first()
        verify_player = db.query(Player).filter(Player.player_id == player_id).first()
        
        print(f'✓ Sala criada: {room_id} por {player_name}')
        print(f'  - Player ID: {player_id}')
        print(f'  - Sala no DB: {verify_room is not None}')
        print(f'  - Player no DB: {verify_player is not None}')
        
        join_room(room_id)
        
        emit('room_created', {
            'room_id': room_id,
            'player': get_player_data(player_id, db),
            'room': get_room_data(room_id, db)
        })
        
    except Exception as e:
        print(f'Erro ao criar sala: {e}')
        db.rollback()
        emit('error', {'message': 'Erro ao criar sala'})
    finally:
        db.close()

@socketio.on('join_room')
def handle_join_room(data):
    db = get_db()
    
    try:
        room_id = data['room_id'].upper()
        player_name = data['player_name']
        player_id = request.sid
        
        print(f'DEBUG - Tentativa de entrar na sala: room_id={room_id}, player={player_name}')
        
        # Listar TODAS as salas no banco
        all_rooms = db.query(Room).all()
        print(f'DEBUG - Total de salas no banco: {len(all_rooms)}')
        for r in all_rooms:
            print(f'  - Sala: {r.room_id}, Host: {r.host_id}, Estado: {r.game_state}')
        
        # Verificar se sala existe
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            print(f'❌ Sala {room_id} não encontrada')
            print(f'   Salas disponíveis: {[r.room_id for r in all_rooms]}')
            emit('error', {'message': f'Sala {room_id} não encontrada'})
            return
        
        if room.game_state != 'waiting':
            emit('error', {'message': 'Jogo já em andamento'})
            return
        
        # Adicionar jogador
        new_player = Player(
            player_id=player_id,
            room_id=room_id,
            name=player_name,
            score=0.0,
            is_host=False
        )
        db.add(new_player)
        db.commit()
        
        join_room(room_id)
        
        emit('room_joined', {
            'room_id': room_id,
            'player': get_player_data(player_id, db),
            'room': get_room_data(room_id, db)
        })
        
        emit('player_joined', {
            'player': get_player_data(player_id, db),
            'players': get_room_players(room_id, db)
        }, room=room_id, include_self=False)
        
        print(f'✓ {player_name} entrou na sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao entrar na sala: {e}')
        db.rollback()
        emit('error', {'message': 'Erro ao entrar na sala'})
    finally:
        db.close()

@socketio.on('update_categories')
def handle_update_categories(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        categories = data['categories']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room:
            emit('error', {'message': 'Sala não encontrada'})
            return
        
        if room.host_id != player_id:
            emit('error', {'message': 'Apenas o criador pode alterar as categorias'})
            return
        
        room.categories = ','.join(categories)
        db.commit()
        
        emit('categories_updated', {'categories': categories}, room=room_id, include_self=True)
        print(f'Categorias atualizadas na sala {room_id}: {categories}')
        
    except Exception as e:
        print(f'Erro ao atualizar categorias: {e}')
        db.rollback()
        emit('error', {'message': 'Erro ao atualizar categorias'})
    finally:
        db.close()

@socketio.on('start_round')
def handle_start_round(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.host_id != player_id:
            emit('error', {'message': 'Apenas o criador pode iniciar a rodada'})
            return
        
        if room.game_state != 'waiting':
            emit('error', {'message': 'Rodada já em andamento'})
            return
        
        # Atualizar estado
        room.current_round += 1
        
        # Selecionar letra que ainda não foi usada
        used_letters_list = room.used_letters.split(',') if room.used_letters else []
        available = [l for l in AVAILABLE_LETTERS if l not in used_letters_list]
        
        # Se todas as letras foram usadas, reiniciar
        if not available:
            available = AVAILABLE_LETTERS
            used_letters_list = []
            print(f'🔄 Todas as letras foram usadas na sala {room_id}, reiniciando ciclo')
        
        # Escolher letra aleatória das disponíveis
        room.current_letter = random.choice(available)
        used_letters_list.append(room.current_letter)
        room.used_letters = ','.join(used_letters_list)
        
        room.game_state = 'playing'  # Ir direto para playing
        db.commit()
        
        print(f'📝 Letra {room.current_letter} sorteada. Letras usadas: {room.used_letters}')
        
        categories = room.categories.split(',')
        
        # Enviar dados da rodada diretamente - countdown será feito no cliente
        emit('round_starting', {
            'countdown': 3,
            'letter': room.current_letter,
            'round': room.current_round,
            'categories': categories
        }, room=room_id)
        
        print(f'Rodada {room.current_round} iniciada na sala {room_id} com letra {room.current_letter}')
    finally:
        db.close()

@socketio.on('submit_answers')
def handle_submit_answers(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        answers = data['answers']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.game_state != 'playing':
            return
        
        current_round = room.current_round
        categories = room.categories.split(',')
        
        # Remover respostas antigas
        db.query(Answer).filter(
            Answer.room_id == room_id,
            Answer.player_id == player_id,
            Answer.round == current_round
        ).delete()
        
        # Adicionar novas respostas (apenas se não estiver vazia)
        for i, answer in enumerate(answers):
            if i < len(categories):
                answer_text = answer.strip() if answer else ''
                # Sempre salvar, mesmo vazio, para manter a estrutura
                new_answer = Answer(
                    room_id=room_id,
                    player_id=player_id,
                    round=current_round,
                    category=categories[i],
                    answer=answer_text,
                    points=0.0,
                    invalidated=False
                )
                db.add(new_answer)
        
        db.commit()
        print(f'Respostas recebidas de {player_id} na sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao submeter respostas: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('stop_game')
def handle_stop_game(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.game_state != 'playing':
            return
        
        player = db.query(Player).filter(Player.player_id == player_id).first()
        player_name = player.name if player else 'Jogador'
        
        room.game_state = 'validation'
        db.commit()
        
        # Pegar todas as respostas
        round_answers = db.query(Answer).filter(
            Answer.room_id == room_id,
            Answer.round == room.current_round
        ).all()
        
        print(f'DEBUG - Total de respostas encontradas: {len(round_answers)}')
        for ans in round_answers:
            print(f'  - Player ID: {ans.player_id}, Categoria: {ans.category}, Resposta: {ans.answer}')
        
        # Pegar todos os jogadores atuais da sala
        current_players = db.query(Player).filter(Player.room_id == room_id).all()
        player_ids_map = {p.player_id: p.player_id for p in current_players}
        
        print(f'DEBUG - Jogadores atuais na sala:')
        for p in current_players:
            print(f'  - {p.name} (ID: {p.player_id})')
        
        # Pegar categorias
        categories_list = room.categories.split(',')
        num_categories = len(categories_list)
        
        # Formatar respostas agrupadas por jogador
        all_answers = {}
        
        # Inicializar com arrays vazios para todos os jogadores
        for p in current_players:
            all_answers[p.player_id] = [''] * num_categories
        
        # Preencher com as respostas reais
        current_letter = room.current_letter
        for ans in round_answers:
            pid = ans.player_id
            # Encontrar o índice da categoria
            try:
                cat_index = categories_list.index(ans.category)
                if pid in all_answers:
                    all_answers[pid][cat_index] = ans.answer
            except ValueError:
                print(f'⚠️ Categoria {ans.category} não encontrada')
        
        # Detectar respostas repetidas por categoria
        repeated_answers = {}  # {categoria: {resposta_lower: [player_ids]}}
        for category in categories_list:
            repeated_answers[category] = {}
            cat_answers = [a for a in round_answers if a.category == category and a.answer]
            for ans in cat_answers:
                answer_lower = ans.answer.lower().strip()
                if answer_lower not in repeated_answers[category]:
                    repeated_answers[category][answer_lower] = []
                repeated_answers[category][answer_lower].append(ans.player_id)
        
        # Marcar validações automáticas
        auto_invalidated = []
        auto_repeated = []
        
        for ans in round_answers:
            if not ans.answer:
                continue
                
            answer_stripped = ans.answer.strip()
            answer_lower = answer_stripped.lower()
            
            try:
                cat_index = categories_list.index(ans.category)
                
                # 1. Verificar se não começa com a letra correta
                if not answer_stripped.upper().startswith(current_letter.upper()):
                    ans.validation_state = 'invalid'
                    ans.invalidated = True
                    auto_invalidated.append({
                        'player_id': ans.player_id,
                        'category_index': cat_index,
                        'reason': 'wrong_letter'
                    })
                    print(f'❌ Letra errada: "{ans.answer}" não começa com {current_letter}')
                
                # 2. Verificar se tem apenas uma letra
                elif len(answer_stripped) == 1:
                    ans.validation_state = 'invalid'
                    ans.invalidated = True
                    auto_invalidated.append({
                        'player_id': ans.player_id,
                        'category_index': cat_index,
                        'reason': 'too_short'
                    })
                    print(f'❌ Muito curta: "{ans.answer}" tem apenas 1 letra')
                
                # 3. Verificar se é repetida
                elif len(repeated_answers[ans.category].get(answer_lower, [])) > 1:
                    # Não invalida, mas marca como repetida para exibição
                    auto_repeated.append({
                        'player_id': ans.player_id,
                        'category_index': cat_index,
                        'answer': ans.answer
                    })
                    print(f'🔁 Repetida: "{ans.answer}" na categoria {ans.category}')
                    
            except ValueError:
                pass
        
        # Salvar as validações automáticas
        db.commit()
        
        all_answers_list = [{'playerId': pid, 'answers': answers} for pid, answers in all_answers.items()]
        
        print(f'DEBUG - Respostas formatadas: {len(all_answers_list)} jogadores com respostas')
        print(f'DEBUG - Auto-invalidadas: {len(auto_invalidated)} respostas')
        print(f'DEBUG - Auto-repetidas: {len(auto_repeated)} respostas')
        
        emit('game_stopped', {
            'stopped_by': player_name,
            'player_id': player_id,
            'all_answers': all_answers_list,
            'auto_invalidated': auto_invalidated,
            'auto_repeated': auto_repeated
        }, room=room_id)
        
        print(f'Jogo parado por {player_name} na sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao parar jogo: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('invalidate_answer')
def handle_invalidate_answer(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        target_player_id = data['player_id']
        category_index = data['category_index']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.game_state != 'validation':
            return
        
        if room.host_id != player_id:
            emit('error', {'message': 'Apenas o criador pode invalidar respostas'})
            return
        
        categories = room.categories.split(',')
        if category_index >= len(categories):
            return
        
        category = categories[category_index]
        
        # Ciclar entre os 3 estados: valid → half → invalid → valid
        answer = db.query(Answer).filter(
            Answer.room_id == room_id,
            Answer.player_id == target_player_id,
            Answer.round == room.current_round,
            Answer.category == category
        ).first()
        
        if answer:
            # Determinar próximo estado
            if answer.validation_state == 'valid':
                answer.validation_state = 'half'
                answer.invalidated = False
            elif answer.validation_state == 'half':
                answer.validation_state = 'invalid'
                answer.invalidated = True
            else:  # invalid
                answer.validation_state = 'valid'
                answer.invalidated = False
            
            db.commit()
            
            emit('answer_validation_changed', {
                'player_id': target_player_id,
                'category_index': category_index,
                'validation_state': answer.validation_state,
                'invalidated': answer.invalidated
            }, room=room_id)
        
    except Exception as e:
        print(f'Erro ao invalidar resposta: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('calculate_scores')
def handle_calculate_scores(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.host_id != player_id or room.game_state != 'validation':
            return
        
        room.game_state = 'scoring'
        db.commit()
        
        current_round = room.current_round
        current_letter = room.current_letter
        categories = room.categories.split(',')
        
        # Pegar respostas
        round_answers = db.query(Answer).filter(
            Answer.room_id == room_id,
            Answer.round == current_round
        ).all()
        
        scores = {}
        detailed_results = []
        
        # Inicializar scores
        room_players = db.query(Player).filter(Player.room_id == room_id).all()
        for p in room_players:
            scores[p.player_id] = 0
        
        # Calcular pontos por categoria
        for category in categories:
            cat_answers = [a for a in round_answers if a.category == category]
            
            # Contar respostas iguais
            answer_counts = {}
            for ans in cat_answers:
                if ans.answer and not ans.invalidated:
                    answer_lower = ans.answer.lower()
                    if answer_lower not in answer_counts:
                        answer_counts[answer_lower] = []
                    answer_counts[answer_lower].append(ans.player_id)
            
            # Atribuir pontos
            for ans in cat_answers:
                if not ans.answer:
                    points = 0
                    reason = 'blank'
                elif ans.validation_state == 'invalid' or ans.invalidated:
                    points = 0
                    reason = 'invalidated'
                elif ans.validation_state == 'half':
                    points = 5  # Meio ponto
                    reason = 'half_point'
                elif not ans.answer.lower().startswith(current_letter.lower()):
                    points = 0
                    reason = 'wrong_letter'
                else:
                    answer_lower = ans.answer.lower()
                    if len(answer_counts.get(answer_lower, [])) == 1:
                        points = 10  # Resposta única
                        reason = 'unique'
                    else:
                        points = 5  # Resposta repetida
                        reason = 'repeated'
                
                scores[ans.player_id] += points
                ans.points = points
                
                detailed_results.append({
                    'playerId': ans.player_id,
                    'category': category,
                    'answer': ans.answer,
                    'points': points,
                    'reason': reason
                })
        
        db.commit()
        
        # Atualizar pontuação total
        for pid, points in scores.items():
            player = db.query(Player).filter(Player.player_id == pid).first()
            if player:
                player.score += points
            else:
                print(f'⚠️ Jogador {pid} não encontrado ao atualizar pontuação')
        
        db.commit()
        
        # Formatar respostas - garantir que todos os jogadores tenham respostas
        all_answers = {}
        
        # Inicializar com arrays vazios para todos os jogadores
        for p in room_players:
            all_answers[p.player_id] = [''] * len(categories)
        
        # Preencher com as respostas reais
        for ans in round_answers:
            pid = ans.player_id
            try:
                cat_index = categories.index(ans.category)
                if pid in all_answers:
                    all_answers[pid][cat_index] = ans.answer
            except ValueError:
                print(f'⚠️ Categoria {ans.category} não encontrada ao formatar respostas')
        
        all_answers_list = [{'playerId': pid, 'answers': answers} for pid, answers in all_answers.items()]
        
        emit('scores_calculated', {
            'scores': scores,
            'detailed_results': detailed_results,
            'players': get_room_players(room_id, db),
            'all_answers': all_answers_list
        }, room=room_id)
        
        print(f'Pontuação calculada para sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao calcular pontuação: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('next_round')
def handle_next_round(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.host_id != player_id:
            return
        
        room.game_state = 'waiting'
        room.current_letter = None
        db.commit()
        
        emit('ready_for_next_round', {}, room=room_id)
        print(f'Sala {room_id} pronta para próxima rodada')
        
    except Exception as e:
        print(f'Erro ao preparar próxima rodada: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('new_match')
def handle_new_match(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.host_id != player_id:
            return
        
        # Zerar pontuação
        db.query(Player).filter(Player.room_id == room_id).update({'score': 0.0})
        
        # Resetar estado da sala
        room.game_state = 'waiting'
        room.current_round = 0
        room.current_letter = None
        room.used_letters = ''  # Resetar letras usadas
        
        # Limpar respostas
        db.query(Answer).filter(Answer.room_id == room_id).delete()
        
        db.commit()
        
        emit('match_reset', {'players': get_room_players(room_id, db)}, room=room_id)
        print(f'Nova partida iniciada na sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao iniciar nova partida: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('kick_player')
def handle_kick_player(data):
    """Expulsar jogador da sala (apenas anfitrião)"""
    db = get_db()
    
    try:
        room_id = data['room_id']
        target_player_id = data['target_player_id']
        host_id = request.sid
        
        # Verificar se quem está expulsando é o anfitrião
        room = db.query(Room).filter(Room.room_id == room_id).first()
        if not room or room.host_id != host_id:
            emit('error', {'message': 'Apenas o anfitrião pode expulsar jogadores'})
            return
        
        # Não pode expulsar a si mesmo
        if target_player_id == host_id:
            emit('error', {'message': 'Você não pode expulsar a si mesmo'})
            return
        
        # Buscar jogador a ser expulso
        target_player = db.query(Player).filter(Player.player_id == target_player_id).first()
        if not target_player or target_player.room_id != room_id:
            return
        
        player_name = target_player.name
        
        # Remover jogador
        db.delete(target_player)
        
        # Remover respostas do jogador
        db.query(Answer).filter(
            Answer.room_id == room_id,
            Answer.player_id == target_player_id
        ).delete()
        
        db.commit()
        
        # Notificar o jogador expulso
        emit('kicked_from_room', {
            'message': 'Você foi removido da sala pelo anfitrião'
        }, room=target_player_id)
        
        # Notificar outros jogadores
        emit('player_kicked', {
            'player_id': target_player_id,
            'player_name': player_name,
            'players': get_room_players(room_id, db)
        }, room=room_id)
        
        print(f'Jogador {player_name} ({target_player_id}) foi expulso da sala {room_id}')
        
    except Exception as e:
        print(f'Erro ao expulsar jogador: {e}')
        db.rollback()
    finally:
        db.close()

@socketio.on('close_room')
def handle_close_room(data):
    db = get_db()
    
    try:
        room_id = data['room_id']
        player_id = request.sid
        
        room = db.query(Room).filter(Room.room_id == room_id).first()
        
        if not room or room.host_id != player_id:
            return
        
        emit('room_closed', {}, room=room_id)
        
        # Deletar sala e dados relacionados
        db.query(Room).filter(Room.room_id == room_id).delete()
        db.query(Player).filter(Player.room_id == room_id).delete()
        db.query(Answer).filter(Answer.room_id == room_id).delete()
        
        db.commit()
        
        print(f'Sala {room_id} fechada pelo host')
        
    except Exception as e:
        print(f'Erro ao fechar sala: {e}')
        db.rollback()
    finally:
        db.close()

# ==================== HELPER FUNCTIONS ====================

def get_player_data(player_id, db):
    player = db.query(Player).filter(Player.player_id == player_id).first()
    if not player:
        return None
    
    return {
        'id': player.player_id,
        'name': player.name,
        'score': float(player.score),
        'isHost': bool(player.is_host)
    }

def get_room_data(room_id, db):
    room = db.query(Room).filter(Room.room_id == room_id).first()
    if not room:
        return None
    
    return {
        'id': room.room_id,
        'host': room.host_id,
        'gameState': room.game_state,
        'currentRound': int(room.current_round),
        'currentLetter': room.current_letter,
        'categories': room.categories.split(','),
        'players': get_room_players(room_id, db)
    }

def get_room_players(room_id, db):
    room_players = db.query(Player).filter(Player.room_id == room_id).all()
    players_list = []
    
    for player in room_players:
        players_list.append({
            'id': player.player_id,
            'name': player.name,
            'score': float(player.score),
            'isHost': bool(player.is_host)
        })
    
    return players_list

@socketio.on('send_chat_message')
def handle_chat_message(data):
    """Recebe uma mensagem de chat de um jogador e retransmite para a sala"""
    room_id = data.get('room_id')
    player_name = data.get('player_name')
    message = data.get('message')

    if not room_id or not message:
        return
    
    # Enviar a mensagem para todos na sala
    emit('chat_message_broadcast', {
        'player_name': player_name,
        'message': message
    }, room=room_id)
    
    print(f'💬 [{room_id}] {player_name}: {message}')

if __name__ == '__main__':
    import socket
    port = int(os.environ.get('PORT', 5000))
    hostname = socket.gethostname()
    local_ip = socket.gethostbyname(hostname)
    
    print('🎮 Servidor Adedonha Python + PostgreSQL rodando...')
    print('📍 Acesso local: http://localhost:5000')
    print(f'📍 Acesso na rede: http://{local_ip}:5000')
    socketio.run(app, host='0.0.0.0', port=port, debug=False)
