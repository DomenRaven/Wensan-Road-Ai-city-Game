import Phaser from 'phaser';
import { ASSETS } from '../assets';
import { CONSTANTS } from '../constants';
import { useGameStore } from '../model/store';
import { startScene } from '../EventBus';

export default class GameScene extends Phaser.Scene {
  private playerPaddle!: Phaser.Physics.Arcade.Image;
  private aiPaddle!: Phaser.Physics.Arcade.Image;
  private ball!: Phaser.Physics.Arcade.Sprite;
  private ballShadow!: Phaser.GameObjects.Image;
  private cursors!: Phaser.Types.Input.Keyboard.CursorKeys;
  private playerScoreImg!: Phaser.GameObjects.Image;
  private aiScoreImg!: Phaser.GameObjects.Image;
  
  private currentBallSpeed: number = CONSTANTS.BALL_INITIAL_SPEED;
  private hitCount: number = 0;
  private isGameOver: boolean = false;
  private lastScoreRef: { player: number, ai: number } = { player: 0, ai: 0 };

  constructor() {
    super('GameScene');
  }

  create() {
    this.isGameOver = false;
    this.currentBallSpeed = CONSTANTS.BALL_INITIAL_SPEED;
    this.hitCount = 0;
    this.lastScoreRef = { player: 0, ai: 0 };

    // Use real background image
    this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2, ASSETS.court_bg)
      .setDisplaySize(CONSTANTS.WIDTH, CONSTANTS.HEIGHT);

    // Center line (dashed)
    this.add.image(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2, ASSETS.court_center_line)
      .setDisplaySize(10, CONSTANTS.HEIGHT)
      .setAlpha(0.5);

    // Player Paddle (Left)
    this.playerPaddle = this.physics.add.image(60, CONSTANTS.HEIGHT / 2, ASSETS.paddle_player)
      .setDisplaySize(CONSTANTS.PADDLE_WIDTH, CONSTANTS.PADDLE_HEIGHT);
    this.playerPaddle.setImmovable(true);
    (this.playerPaddle.body as Phaser.Physics.Arcade.Body).setAllowGravity(false);
    this.playerPaddle.setCollideWorldBounds(true);

    // AI Paddle (Right)
    this.aiPaddle = this.physics.add.image(CONSTANTS.WIDTH - 60, CONSTANTS.HEIGHT / 2, ASSETS.paddle_ai)
      .setDisplaySize(CONSTANTS.PADDLE_WIDTH, CONSTANTS.PADDLE_HEIGHT);
    this.aiPaddle.setImmovable(true);
    (this.aiPaddle.body as Phaser.Physics.Arcade.Body).setAllowGravity(false);
    this.aiPaddle.setCollideWorldBounds(true);

    // Ball
    this.ball = this.physics.add.sprite(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2, ASSETS.ball, 0)
      .setDisplaySize(CONSTANTS.BALL_SIZE, CONSTANTS.BALL_SIZE);
    this.ball.setBounce(1, 1);
    this.ball.setCollideWorldBounds(true);
    (this.ball.body as Phaser.Physics.Arcade.Body).onWorldBounds = true;
    
    // Play ball spin animation
    this.ball.play('ball_spin');

    // Input
    if (this.input.keyboard) {
      this.cursors = this.input.keyboard.createCursorKeys();
      this.input.keyboard.addCapture('UP,DOWN');
    }

    // Score HUD
    this.playerScoreImg = this.add.image(CONSTANTS.WIDTH / 2 - 100, 80, ASSETS.score_digits, 0)
      .setDisplaySize(51, 96);
      
    this.aiScoreImg = this.add.image(CONSTANTS.WIDTH / 2 + 100, 80, ASSETS.score_digits, 0)
      .setDisplaySize(51, 96);

    // Collisions
    this.physics.add.collider(this.ball, this.playerPaddle, this.handlePaddleHit, undefined, this);
    this.physics.add.collider(this.ball, this.aiPaddle, this.handlePaddleHit, undefined, this);
    
    // Bounds collision for scoring
    this.physics.world.on('worldbounds', (body: Phaser.Physics.Arcade.Body, up: boolean, down: boolean, left: boolean, right: boolean) => {
      if (this.isGameOver) return;
      if (left) {
        this.handleScore('ai');
      } else if (right) {
        this.handleScore('player');
      }
    });

    useGameStore.getState().setStatus('playing');

    // Start round
    this.time.delayedCall(1000, () => {
      this.resetBall(-1);
    });
  }

  private handlePaddleHit(ballObj: any, paddleObj: any) {
    if (this.isGameOver) return;

    const ball = ballObj as Phaser.Physics.Arcade.Sprite;
    const paddle = paddleObj as Phaser.Physics.Arcade.Image;

    // Increment hit count
    this.hitCount++;
    if (this.hitCount % 3 === 0) {
      this.currentBallSpeed += CONSTANTS.BALL_SPEED_INCREMENT;
    }

    // Calculate angle based on where it hit the paddle
    let diff = 0;
    if (ball.y < paddle.y) {
      diff = paddle.y - ball.y;
      ball.setVelocityY(-10 * diff);
    } else if (ball.y > paddle.y) {
      diff = ball.y - paddle.y;
      ball.setVelocityY(10 * diff);
    } else {
      ball.setVelocityY(2 + Math.random() * 8);
    }

    // Ensure ball speed
    const currentVelocity = ball.body!.velocity;
    const isPlayer = paddle === this.playerPaddle;
    
    // Calculate random fluctuation factor (0.85 to 1.15)
    const factor = 0.85 + Math.random() * 0.3;
    const newSpeed = this.currentBallSpeed * factor;
    const direction = isPlayer ? 1 : -1;
    
    ball.setVelocityX(direction * newSpeed);
  }

  private handleScore(winner: 'player' | 'ai') {
    if (this.isGameOver) return;
    
    const store = useGameStore.getState();
    if (winner === 'player') {
      store.addPlayerScore();
      // Screen shake effect for scoring
      this.cameras.main.shake(200, 0.01);
      // Zoom text
      this.tweens.add({
        targets: this.playerScoreImg,
        scaleX: 1.5, scaleY: 1.5,
        duration: 100, yoyo: true
      });
    } else {
      store.addAiScore();
      this.cameras.main.shake(200, 0.01);
      this.tweens.add({
        targets: this.aiScoreImg,
        scaleX: 1.5, scaleY: 1.5,
        duration: 100, yoyo: true
      });
    }

    // Update displays after a short delay to allow React state to sync
    // We can also sync directly here
    const { playerScore, aiScore } = useGameStore.getState();
    this.updateScoreDisplay(playerScore, aiScore);

    if (playerScore >= CONSTANTS.WIN_SCORE || aiScore >= CONSTANTS.WIN_SCORE) {
      this.isGameOver = true;
      store.setWinner(playerScore >= CONSTANTS.WIN_SCORE ? 'player' : 'ai');
      this.ball.setVelocity(0, 0);
      this.time.delayedCall(1000, () => {
        startScene(this, 'EndScene');
      });
    } else {
      // Reset ball
      this.ball.setVelocity(0, 0);
      this.ball.setPosition(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2);
      this.time.delayedCall(1000, () => {
        this.resetBall(winner === 'player' ? -1 : 1); // Serve to the loser
      });
    }
  }

  private updateScoreDisplay(player: number, ai: number) {
    if (player !== this.lastScoreRef.player) {
      this.playerScoreImg.setFrame(Math.min(9, player));
      this.lastScoreRef.player = player;
    }
    if (ai !== this.lastScoreRef.ai) {
      this.aiScoreImg.setFrame(Math.min(9, ai));
      this.lastScoreRef.ai = ai;
    }
  }

  private resetBall(direction: number) {
    if (this.isGameOver) return;
    this.currentBallSpeed = CONSTANTS.BALL_INITIAL_SPEED;
    this.hitCount = 0;
    
    this.ball.setPosition(CONSTANTS.WIDTH / 2, CONSTANTS.HEIGHT / 2);
    this.ball.setVelocity(
      direction * this.currentBallSpeed, 
      (Math.random() - 0.5) * this.currentBallSpeed
    );
    
    // Reset paddles
    (this.playerPaddle.body as Phaser.Physics.Arcade.Body).reset(60, CONSTANTS.HEIGHT / 2);
    (this.aiPaddle.body as Phaser.Physics.Arcade.Body).reset(CONSTANTS.WIDTH - 60, CONSTANTS.HEIGHT / 2);
  }

  update() {
    if (this.isGameOver) return;

    // Player input
    const playerBody = this.playerPaddle.body as Phaser.Physics.Arcade.Body;
    if (this.cursors.up.isDown) {
      playerBody.setVelocityY(-CONSTANTS.PADDLE_SPEED);
    } else if (this.cursors.down.isDown) {
      playerBody.setVelocityY(CONSTANTS.PADDLE_SPEED);
    } else {
      playerBody.setVelocityY(0);
    }

    // Simple AI
    const aiBody = this.aiPaddle.body as Phaser.Physics.Arcade.Body;
    const aiSpeed = CONSTANTS.AI_SPEED;
    // AI only moves if the ball is moving towards it
    if (this.ball.body!.velocity.x > 0) {
      if (this.aiPaddle.y < this.ball.y - 10) {
        aiBody.setVelocityY(aiSpeed);
      } else if (this.aiPaddle.y > this.ball.y + 10) {
        aiBody.setVelocityY(-aiSpeed);
      } else {
        aiBody.setVelocityY(0);
      }
    } else {
      // Return to center slowly
      if (this.aiPaddle.y < CONSTANTS.HEIGHT / 2 - 10) {
        aiBody.setVelocityY(aiSpeed * 0.5);
      } else if (this.aiPaddle.y > CONSTANTS.HEIGHT / 2 + 10) {
        aiBody.setVelocityY(-aiSpeed * 0.5);
      } else {
        aiBody.setVelocityY(0);
      }
    }

    // Sync score if external
    const { playerScore, aiScore } = useGameStore.getState();
    this.updateScoreDisplay(playerScore, aiScore);
  }
}
